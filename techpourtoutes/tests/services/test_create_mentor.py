from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings


def _mock_jobirl_registration(*, success=True, user_id=287565, token="tpt_abc", errors=None):
    return MagicMock(
        success=success,
        failure=not success,
        errors=errors or [],
        user_id=user_id if success else None,
        token=token if success else None,
    )


def _unsaved_pro(valid_pro_model_data):
    from techpourtoutes.models import Pro

    return Pro(**valid_pro_model_data, username=valid_pro_model_data["email"])


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_calls_jobirl_with_mentor(valid_pro_model_data):
    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration()

    with patch(
        "techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock
    ) as MockRegister:
        CreateMentor(pro=pro)

    MockRegister.assert_called_once_with(pro=pro)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_saves_mentor_with_jobirl_fields(valid_pro_model_data):
    from techpourtoutes.models import Pro
    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration()

    with patch("techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock):
        result = CreateMentor(pro=pro)

    assert result.success is True
    db_pro = Pro.objects.get(email=valid_pro_model_data["email"])
    assert db_pro.jobirl_user_id == 287565
    assert db_pro.jobirl_user_token == "tpt_abc"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_sends_welcome_email(valid_pro_model_data):
    from django.core import mail

    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration()

    with patch("techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock):
        CreateMentor(pro=pro)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [valid_pro_model_data["email"]]
    assert "Bienvenue" in mail.outbox[0].subject


@pytest.mark.django_db
def test_create_mentor_on_jobirl_failure_propagates_errors(valid_pro_model_data):
    from techpourtoutes.models import Pro
    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration(success=False, errors=["erreur de synchronisation"])

    with patch("techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock):
        result = CreateMentor(pro=pro)

    assert result.failure is True
    assert result.errors == ["erreur de synchronisation"]
    assert not Pro.objects.filter(email=valid_pro_model_data["email"]).exists()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_adds_mentor_engagement(valid_pro_model_data):
    from techpourtoutes.models import Pro
    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    mock = _mock_jobirl_registration()

    with patch("techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock):
        CreateMentor(pro=pro)

    db_pro = Pro.objects.get(email=valid_pro_model_data["email"])
    assert "mentor" in db_pro.engagements


@pytest.mark.django_db(transaction=True)
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_mentor_syncs_contact_to_brevo(valid_pro_model_data, mock_brevo_sdk):
    from techpourtoutes.services.create_mentor import CreateMentor

    pro = _unsaved_pro(valid_pro_model_data)
    pro.brevo_sync_enabled = True
    mock = _mock_jobirl_registration()

    with patch("techpourtoutes.services.create_mentor.RegisterMentorOnJobirl", return_value=mock):
        result = CreateMentor(pro=pro)

    assert result.success is True
    create_contact = mock_brevo_sdk.return_value.contacts.create_contact
    create_contact.assert_called()
    call_kwargs = create_contact.call_args.kwargs
    assert call_kwargs["email"] == valid_pro_model_data["email"]
    assert call_kwargs["ext_id"] == str(pro.pk)
    assert call_kwargs["update_enabled"] is True
    assert call_kwargs["list_ids"] == [42]
    assert call_kwargs["attributes"]["PRENOM"] == valid_pro_model_data["first_name"]
    assert call_kwargs["attributes"]["NOM"] == valid_pro_model_data["last_name"]


@pytest.mark.django_db
def test_create_mentor_existing_pro_sends_new_engagement(pro):
    from techpourtoutes.mailers import ProMailer
    from techpourtoutes.services.create_mentor import CreateMentor

    mock = _mock_jobirl_registration()

    with (
        patch(
            "techpourtoutes.services.create_mentor.RegisterMentorOnJobirl",
            return_value=mock,
        ),
        patch.object(
            ProMailer,
            "new_engagement",
        ) as new_engagement,
        patch.object(
            ProMailer,
            "welcome",
        ) as welcome,
    ):
        CreateMentor(pro=pro)

    new_engagement.assert_called_once_with(pro=pro)
    welcome.assert_not_called()
