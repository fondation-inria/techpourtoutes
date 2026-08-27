from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.models import Pro
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.pro.create_mentor import CreateMentor

REGISTER = "techpourtoutes.services.pro.create_mentor.RegisterUserOnJobirl"
TASK = "techpourtoutes.services.pro.create_mentor.create_mentor_task"

pytestmark = pytest.mark.django_db


def _unsaved_pro(valid_pro_model_data):
    return Pro(**valid_pro_model_data, username=valid_pro_model_data["email"])


def _registered():
    return MagicMock(success=True, failure=False, errors=[], user_id=287565, token="tpt_abc")


def _registration_failed(*errors, transient):
    return MagicMock(
        success=False,
        failure=True,
        errors=list(errors),
        failed_with_transient_error=transient,
        error_kind=ErrorKind.TRANSIENT if transient else ErrorKind.PERMANENT,
    )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_saves_the_pro_with_its_engagement_and_jobirl_fields(valid_pro_model_data):
    pro = _unsaved_pro(valid_pro_model_data)

    with patch(REGISTER, return_value=_registered()) as MockRegister:
        result = CreateMentor(pro=pro)

    MockRegister.assert_called_once_with(user=pro, is_pro=True)
    assert result.success is True
    db_pro = Pro.objects.get(email=valid_pro_model_data["email"])
    assert "mentor" in db_pro.engagements
    assert db_pro.jobirl_user_id == 287565
    assert db_pro.jobirl_user_token == "tpt_abc"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_sends_welcome_email(valid_pro_model_data):
    from django.core import mail

    with patch(REGISTER, return_value=_registered()):
        CreateMentor(pro=_unsaved_pro(valid_pro_model_data))

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [valid_pro_model_data["email"]]
    assert "Bienvenue" in mail.outbox[0].subject


def test_create_mentor_existing_pro_sends_new_engagement(pro):
    from techpourtoutes.mailers import ProMailer

    with (
        patch(REGISTER, return_value=_registered()),
        patch.object(ProMailer, "new_engagement") as new_engagement,
        patch.object(ProMailer, "welcome") as welcome,
    ):
        CreateMentor(pro=pro)

    new_engagement.assert_called_once_with(pro=pro)
    welcome.assert_not_called()


@pytest.mark.django_db(transaction=True)
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_syncs_contact_to_brevo(valid_pro_model_data, mock_brevo_sdk):
    pro = _unsaved_pro(valid_pro_model_data)
    pro.brevo_sync_enabled = True

    with patch(REGISTER, return_value=_registered()):
        result = CreateMentor(pro=pro)

    assert result.success is True
    create_contact = mock_brevo_sdk.return_value.contacts.create_contact
    create_contact.assert_called()
    call_kwargs = create_contact.call_args.kwargs
    assert call_kwargs["email"] == valid_pro_model_data["email"]
    assert call_kwargs["ext_id"] == str(pro.pk)
    assert call_kwargs["list_ids"] == [42]


@pytest.mark.django_db(transaction=True)
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_a_transient_jobirl_failure_is_handed_to_a_task_without_blocking(valid_pro_model_data):
    pro = _unsaved_pro(valid_pro_model_data)
    failed = _registration_failed("Jobirl injoignable.", transient=True)

    with patch(REGISTER, return_value=failed), patch(TASK) as task:
        result = CreateMentor(pro=pro)

    assert result.success is True
    assert Pro.objects.filter(email=valid_pro_model_data["email"]).exists()
    task.delay.assert_called_once_with(pro_pk=str(pro.pk))


def test_a_refused_registration_leaves_the_pro_object_as_it_found_it(pro):
    """The view re-renders the very instance it handed over, and reads engagements off it."""
    failed = _registration_failed("EMAIL ALREADY EXISTS", transient=False)

    with patch(REGISTER, return_value=failed):
        CreateMentor(pro=pro)

    assert "mentor" not in pro.engagements
    pro.refresh_from_db()
    assert "mentor" not in pro.engagements


@pytest.mark.django_db(transaction=True)
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_a_refused_jobirl_registration_rolls_the_whole_pro_back(valid_pro_model_data):
    from django.core import mail

    pro = _unsaved_pro(valid_pro_model_data)
    failed = _registration_failed("EMAIL ALREADY EXISTS", transient=False)

    with patch(REGISTER, return_value=failed), patch(TASK) as task:
        result = CreateMentor(pro=pro)

    assert result.failure is True
    assert result.errors == ["EMAIL ALREADY EXISTS"]
    assert not Pro.objects.filter(email=valid_pro_model_data["email"]).exists()
    assert mail.outbox == []
    task.delay.assert_not_called()
