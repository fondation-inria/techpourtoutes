from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.models import Beneficiary
from techpourtoutes.services.beneficiary.create_beneficiary import CreateBeneficiary
from techpourtoutes.tasks import send_beneficiary_welcome_email_task

CREATE_MENTOREE = "techpourtoutes.services.beneficiary.create_beneficiary.CreateMentoree"


def _training_experience_form():
    form = MagicMock()
    form.has_missing_record = False
    return form


def _minor_mentoring_data():
    return {
        "phone": "0612345678",
        "legal_representative_name": "Parent Test",
        "legal_representative_email": "parent@example.com",
    }


def _create_beneficiary(**overrides):
    kwargs = {
        "email": "lea@example.com",
        "first_name": "Léa",
        "last_name": "Petit",
        "birth_date": date(1995, 1, 1),
        "newsletter_consent": True,
        "training_experience_form": _training_experience_form(),
        "wants_mentor": False,
    }
    kwargs.update(overrides)
    with patch.object(send_beneficiary_welcome_email_task, "apply_async"):
        return CreateBeneficiary(**kwargs)


@pytest.mark.django_db
def test_create_beneficiary_saves_beneficiary_with_expected_fields():
    result = _create_beneficiary()

    assert result.success is True
    beneficiary = Beneficiary.objects.get(email="lea@example.com")
    assert beneficiary.first_name == "Léa"
    assert beneficiary.last_name == "Petit"
    assert beneficiary.birth_date == date(1995, 1, 1)
    assert beneficiary.brevo_sync_enabled is True
    assert beneficiary.phone == ""
    assert beneficiary.legal_representative_name == ""
    assert beneficiary.legal_representative_email == ""
    assert result.beneficiary == beneficiary
    assert result.mentoring_errors == []


@pytest.mark.django_db
def test_create_beneficiary_saves_training_experience():
    form = _training_experience_form()

    result = _create_beneficiary(training_experience_form=form)

    form.save.assert_called_once_with(result.beneficiary)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_beneficiary_sends_login_code_email():
    from django.core import mail

    _create_beneficiary()

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["lea@example.com"]


@pytest.mark.django_db
def test_create_beneficiary_schedules_welcome_email_task():
    with patch.object(send_beneficiary_welcome_email_task, "apply_async") as apply_async:
        result = CreateBeneficiary(
            email="lea@example.com",
            first_name="Léa",
            last_name="Petit",
            birth_date=date(1995, 1, 1),
            newsletter_consent=True,
            training_experience_form=_training_experience_form(),
            wants_mentor=False,
        )

    apply_async.assert_called_once_with(
        kwargs={"beneficiary_pk": str(result.beneficiary.pk)}, countdown=5 * 60
    )


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_create_beneficiary_wants_mentor_and_minor_persists_legal_representative():
    from django.core import mail

    with patch(CREATE_MENTOREE) as MockCreateMentoree:
        result = _create_beneficiary(
            birth_date=date.today().replace(year=date.today().year - 16),
            wants_mentor=True,
            mentoring_signup_data=_minor_mentoring_data(),
        )

    MockCreateMentoree.assert_not_called()
    assert result.beneficiary.phone == "+33612345678"
    assert result.beneficiary.legal_representative_name == "Parent Test"
    assert result.beneficiary.legal_representative_email == "parent@example.com"
    assert "Nouvelle attestation à envoyer" in {message.subject for message in mail.outbox}
    assert result.mentoring_errors == []


@pytest.mark.django_db
def test_create_beneficiary_wants_mentor_and_adult_registers_with_jobirl():
    mock = MagicMock(success=True, failure=False, errors=[])

    with patch(CREATE_MENTOREE, return_value=mock) as MockCreateMentoree:
        result = _create_beneficiary(
            birth_date=date.today().replace(year=date.today().year - 20),
            wants_mentor=True,
            mentoring_signup_data=_minor_mentoring_data(),
        )

    MockCreateMentoree.assert_called_once_with(beneficiary=result.beneficiary)
    assert result.beneficiary.phone == "+33612345678"
    # An adult never has a legal representative, even if the form data carried one.
    assert result.beneficiary.legal_representative_name == ""
    assert result.beneficiary.legal_representative_email == ""
    assert result.mentoring_errors == []


@pytest.mark.django_db
def test_create_beneficiary_collects_jobirl_registration_errors_without_failing():
    mock = MagicMock(success=False, failure=True, errors=["Jobirl est indisponible."])

    with patch(CREATE_MENTOREE, return_value=mock):
        result = _create_beneficiary(
            birth_date=date.today().replace(year=date.today().year - 20),
            wants_mentor=True,
            mentoring_signup_data=_minor_mentoring_data(),
        )

    assert result.success is True
    assert result.mentoring_errors == ["Jobirl est indisponible."]
    assert Beneficiary.objects.filter(pk=result.beneficiary.pk).exists()
