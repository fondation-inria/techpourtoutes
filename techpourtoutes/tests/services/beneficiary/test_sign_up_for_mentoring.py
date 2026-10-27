from unittest.mock import MagicMock, patch

import pytest
from django.core import mail

from techpourtoutes.models import LegalRepresentativeAuthorization
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.beneficiary.sign_up_for_mentoring import SignUpForMentoring

CREATE_MENTOREE = "techpourtoutes.services.beneficiary.sign_up_for_mentoring.CreateMentoree"
TASK = "techpourtoutes.services.beneficiary.sign_up_for_mentoring.create_mentoree_task"


def _registered():
    return MagicMock(success=True, failure=False, errors=[], failed_with_transient_error=False)


def _registration_failed(*errors, transient):
    return MagicMock(
        success=False,
        failure=True,
        errors=list(errors),
        failed_with_transient_error=transient,
        error_kind=ErrorKind.TRANSIENT if transient else ErrorKind.PERMANENT,
    )


MENTORING_DATA = {
    "phone": "0612345678",
    "legal_representative_name": "Parent Test",
    "legal_representative_email": "parent@example.com",
}


def _sign_up(beneficiary, *, is_minor=False):
    return SignUpForMentoring(
        beneficiary=beneficiary, is_minor=is_minor, mentoring_signup_data=MENTORING_DATA
    )


@pytest.mark.django_db
def test_a_minor_waits_for_her_legal_representative_authorization_instead_of_jobirl(
    beneficiary,
):
    with patch(CREATE_MENTOREE) as MockCreateMentoree:
        result = _sign_up(beneficiary, is_minor=True)

    assert result.success is True
    MockCreateMentoree.assert_not_called()
    authorization = beneficiary.legal_representative_authorization
    assert authorization.legal_representative_name == "Parent Test"
    assert authorization.legal_representative_email == "parent@example.com"
    assert mail.outbox[0].to == ["parent@example.com"]


@pytest.mark.django_db
def test_an_adult_is_registered_on_jobirl(beneficiary):
    with (
        patch(CREATE_MENTOREE, return_value=_registered()) as MockCreateMentoree,
        patch(TASK) as task,
    ):
        result = _sign_up(beneficiary)

    assert result.success is True
    MockCreateMentoree.assert_called_once_with(beneficiary=beneficiary)
    task.delay.assert_not_called()
    # An adult never has a legal representative, even if the form data carried one.
    assert not LegalRepresentativeAuthorization.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_a_transient_failure_is_handed_to_a_task_without_blocking(beneficiary):
    failed = _registration_failed("Jobirl injoignable.", transient=True)

    with patch(CREATE_MENTOREE, return_value=failed), patch(TASK) as task:
        result = _sign_up(beneficiary)

    assert result.success is True
    task.delay.assert_called_once_with(beneficiary_pk=str(beneficiary.pk))


@pytest.mark.django_db(transaction=True)
def test_a_permanent_failure_blocks_and_carries_its_message_up(beneficiary):
    failed = _registration_failed("EMAIL ALREADY EXISTS", transient=False)

    with patch(CREATE_MENTOREE, return_value=failed), patch(TASK) as task:
        result = _sign_up(beneficiary)

    assert result.failure is True
    assert result.errors == ["EMAIL ALREADY EXISTS"]
    task.delay.assert_not_called()
