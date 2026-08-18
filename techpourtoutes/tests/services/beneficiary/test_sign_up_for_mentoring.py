from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.beneficiary.sign_up_for_mentoring import SignUpForMentoring

CREATE_MENTOREE = "techpourtoutes.services.beneficiary.sign_up_for_mentoring.CreateMentoree"
TASK = "techpourtoutes.services.beneficiary.sign_up_for_mentoring.create_mentoree_task"

MENTORING_DATA = {
    "phone": "0612345678",
    "legal_representative_name": "Parent Test",
    "legal_representative_email": "parent@example.com",
}


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


def _sign_up(beneficiary, *, is_minor=False):
    return SignUpForMentoring(
        beneficiary=beneficiary, is_minor=is_minor, mentoring_signup_data=MENTORING_DATA
    )


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_a_minor_is_handed_over_to_the_consortium_instead_of_jobirl(beneficiary):
    from django.core import mail

    with patch(CREATE_MENTOREE) as MockCreateMentoree:
        result = _sign_up(beneficiary, is_minor=True)

    assert result.success is True
    MockCreateMentoree.assert_not_called()
    assert "Nouvelle attestation à envoyer" in {message.subject for message in mail.outbox}


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
