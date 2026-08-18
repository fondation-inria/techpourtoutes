from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.services.beneficiary.add_mentoring import AddMentoring

SIGN_UP_FOR_MENTORING = "techpourtoutes.services.beneficiary.add_mentoring.SignUpForMentoring"

MENTORING_DATA = {
    "phone": "+33687654321",
    "legal_representative_name": "",
    "legal_representative_email": "",
}


def _succeeded():
    return MagicMock(success=True, failure=False, errors=[])


def _failed(*errors):
    return MagicMock(success=False, failure=True, errors=list(errors))


@pytest.mark.django_db
def test_updates_phone_and_signs_up_an_adult(beneficiary):
    with patch(SIGN_UP_FOR_MENTORING, return_value=_succeeded()) as MockSignUp:
        result = AddMentoring(beneficiary=beneficiary, mentoring_signup_data=MENTORING_DATA)

    assert result.success is True
    beneficiary.refresh_from_db()
    assert beneficiary.phone == "+33687654321"
    MockSignUp.assert_called_once_with(
        beneficiary=beneficiary, is_minor=False, mentoring_signup_data=MENTORING_DATA
    )


@pytest.mark.django_db
def test_saves_legal_representative_for_a_minor(beneficiary):
    beneficiary.birth_date = date(2012, 1, 1)
    beneficiary.save()
    data = {
        **MENTORING_DATA,
        "legal_representative_name": "Parent Test",
        "legal_representative_email": "parent@example.com",
    }

    with patch(SIGN_UP_FOR_MENTORING, return_value=_succeeded()) as MockSignUp:
        result = AddMentoring(beneficiary=beneficiary, mentoring_signup_data=data)

    assert result.success is True
    beneficiary.refresh_from_db()
    assert beneficiary.legal_representative_name == "Parent Test"
    assert beneficiary.legal_representative_email == "parent@example.com"
    MockSignUp.assert_called_once_with(
        beneficiary=beneficiary, is_minor=True, mentoring_signup_data=data
    )


@pytest.mark.django_db
def test_relays_sign_up_failure(beneficiary):
    with patch(SIGN_UP_FOR_MENTORING, return_value=_failed("Jobirl error")):
        result = AddMentoring(beneficiary=beneficiary, mentoring_signup_data=MENTORING_DATA)

    assert result.failure is True
    assert result.errors == ["Jobirl error"]
