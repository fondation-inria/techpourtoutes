from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.models import Beneficiary
from techpourtoutes.services.beneficiary.upsert_beneficiary import UpsertBeneficiary
from techpourtoutes.tasks import send_beneficiary_welcome_email_task

SIGN_UP = "techpourtoutes.services.beneficiary.upsert_beneficiary.SignUpForMentoring"


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


def _signed_up():
    return MagicMock(success=True, failure=False, errors=[])


def _sign_up_refused(*errors):
    return MagicMock(success=False, failure=True, errors=list(errors))


def _beneficiary_data(**overrides):
    data = {
        "email": "lea@example.com",
        "first_name": "Léa",
        "last_name": "Petit",
        "birth_date": date(1995, 1, 1),
        "newsletter_consent": True,
    }
    data.update(overrides)
    return data


def _create_beneficiary(**overrides):
    training_experience_form = overrides.pop(
        "training_experience_form", _training_experience_form()
    )
    beneficiary_data = _beneficiary_data(
        **{k: v for k, v in overrides.items() if k != "mentoring_signup_data"}
    )
    with patch.object(send_beneficiary_welcome_email_task, "apply_async"):
        return UpsertBeneficiary(
            beneficiary_data=beneficiary_data,
            training_experience_form=training_experience_form,
            mentoring_signup_data=overrides.get("mentoring_signup_data"),
        )


# ------------------- creating a new beneficiary -------------------


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
        result = UpsertBeneficiary(
            beneficiary_data=_beneficiary_data(),
            training_experience_form=_training_experience_form(),
        )

    apply_async.assert_called_once_with(
        kwargs={"beneficiary_pk": str(result.beneficiary.pk)}, countdown=5 * 60
    )


@pytest.mark.django_db
def test_create_beneficiary_wants_mentor_and_minor_persists_legal_representative():
    with patch(SIGN_UP, return_value=_signed_up()) as MockSignUp:
        result = _create_beneficiary(
            birth_date=date.today().replace(year=date.today().year - 16),
            mentoring_signup_data=_minor_mentoring_data(),
        )

    assert result.beneficiary.phone == "+33612345678"
    assert result.beneficiary.legal_representative_name == "Parent Test"
    assert result.beneficiary.legal_representative_email == "parent@example.com"
    assert MockSignUp.call_args.kwargs["is_minor"] is True


@pytest.mark.django_db
def test_create_beneficiary_wants_mentor_and_adult_signs_up_for_mentoring():
    with patch(SIGN_UP, return_value=_signed_up()) as MockSignUp:
        result = _create_beneficiary(
            birth_date=date.today().replace(year=date.today().year - 20),
            mentoring_signup_data=_minor_mentoring_data(),
        )

    MockSignUp.assert_called_once_with(
        beneficiary=result.beneficiary,
        is_minor=False,
        mentoring_signup_data=_minor_mentoring_data(),
    )
    assert result.beneficiary.phone == "+33612345678"
    # An adult never has a legal representative, even if the form data carried one.
    assert result.beneficiary.legal_representative_name == ""
    assert result.beneficiary.legal_representative_email == ""


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_a_refused_mentoring_sign_up_rolls_the_whole_account_back():
    from django.core import mail

    refused = _sign_up_refused("EMAIL ALREADY EXISTS")

    with patch(SIGN_UP, return_value=refused):
        with patch.object(send_beneficiary_welcome_email_task, "apply_async") as apply_async:
            result = UpsertBeneficiary(
                beneficiary_data=_beneficiary_data(
                    birth_date=date.today().replace(year=date.today().year - 20)
                ),
                training_experience_form=_training_experience_form(),
                mentoring_signup_data=_minor_mentoring_data(),
            )

    assert result.failure is True
    assert result.errors == ["EMAIL ALREADY EXISTS"]
    assert not Beneficiary.objects.filter(email="lea@example.com").exists()
    assert mail.outbox == []
    apply_async.assert_not_called()


# ------------------- adding mentoring to an existing beneficiary -------------------


@pytest.mark.django_db
def test_updates_phone_and_signs_up_an_adult(beneficiary):
    with patch(SIGN_UP, return_value=_signed_up()) as MockSignUp:
        result = UpsertBeneficiary(
            beneficiary=beneficiary, mentoring_signup_data=_minor_mentoring_data()
        )

    assert result.success is True
    beneficiary.refresh_from_db()
    assert beneficiary.phone == "+33612345678"
    MockSignUp.assert_called_once_with(
        beneficiary=beneficiary, is_minor=False, mentoring_signup_data=_minor_mentoring_data()
    )


@pytest.mark.django_db
def test_saves_legal_representative_for_a_minor(beneficiary):
    beneficiary.birth_date = date(2012, 1, 1)
    beneficiary.save()
    data = {
        **_minor_mentoring_data(),
        "legal_representative_name": "Parent Test",
        "legal_representative_email": "parent@example.com",
    }

    with patch(SIGN_UP, return_value=_signed_up()) as MockSignUp:
        result = UpsertBeneficiary(beneficiary=beneficiary, mentoring_signup_data=data)

    assert result.success is True
    beneficiary.refresh_from_db()
    assert beneficiary.legal_representative_name == "Parent Test"
    assert beneficiary.legal_representative_email == "parent@example.com"
    MockSignUp.assert_called_once_with(
        beneficiary=beneficiary, is_minor=True, mentoring_signup_data=data
    )


@pytest.mark.django_db
def test_relays_sign_up_failure(beneficiary):
    with patch(SIGN_UP, return_value=_sign_up_refused("Jobirl error")):
        result = UpsertBeneficiary(
            beneficiary=beneficiary, mentoring_signup_data=_minor_mentoring_data()
        )

    assert result.failure is True
    assert result.errors == ["Jobirl error"]


@pytest.mark.django_db
def test_adding_mentoring_to_an_existing_beneficiary_sends_no_onboarding_email(beneficiary):
    with patch(SIGN_UP, return_value=_signed_up()):
        with patch.object(send_beneficiary_welcome_email_task, "apply_async") as apply_async:
            UpsertBeneficiary(
                beneficiary=beneficiary, mentoring_signup_data=_minor_mentoring_data()
            )

    apply_async.assert_not_called()
