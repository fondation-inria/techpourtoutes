from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.django_db
def test_create_mentoree_calls_jobirl_with_user_and_saves_result(beneficiary):
    from techpourtoutes.services.beneficiary.create_mentoree import CreateMentoree

    mock = MagicMock(success=True, failure=False, errors=[], user_id=287565, token="tpt_abc")

    with patch(
        "techpourtoutes.services.create_mentoree.RegisterUserOnJobirl", return_value=mock
    ) as MockRegister:
        result = CreateMentoree(beneficiary=beneficiary)

    MockRegister.assert_called_once_with(user=beneficiary)
    assert result.success is True
    beneficiary.refresh_from_db()
    assert beneficiary.jobirl_user_id == 287565
    assert beneficiary.jobirl_user_token == "tpt_abc"
