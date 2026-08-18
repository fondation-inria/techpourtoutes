from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.beneficiary.create_mentoree import CreateMentoree

REGISTER = "techpourtoutes.services.beneficiary.create_mentoree.RegisterUserOnJobirl"


@pytest.mark.django_db
def test_create_mentoree_calls_jobirl_with_user_and_saves_result(beneficiary):
    mock = MagicMock(success=True, failure=False, errors=[], user_id=287565, token="tpt_abc")

    with patch(REGISTER, return_value=mock) as MockRegister:
        result = CreateMentoree(beneficiary=beneficiary)

    MockRegister.assert_called_once_with(user=beneficiary, is_pro=False)
    assert result.success is True
    beneficiary.refresh_from_db()
    assert beneficiary.jobirl_user_id == 287565
    assert beneficiary.jobirl_user_token == "tpt_abc"


@pytest.mark.django_db
def test_create_mentoree_relays_the_registration_failure_and_its_kind(beneficiary):
    """Whoever called it decides what to do, and only ever sees CreateMentoree."""
    mock = MagicMock(
        success=False,
        failure=True,
        errors=["Jobirl est indisponible."],
        error_kind=ErrorKind.TRANSIENT,
    )

    with patch(REGISTER, return_value=mock):
        result = CreateMentoree(beneficiary=beneficiary)

    assert result.failure is True
    assert result.errors == ["Jobirl est indisponible."]
    assert result.error_kind is ErrorKind.TRANSIENT
    beneficiary.refresh_from_db()
    assert beneficiary.jobirl_user_id is None
