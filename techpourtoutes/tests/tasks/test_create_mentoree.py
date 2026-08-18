from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.tasks._retry import TransientError
from techpourtoutes.tasks.create_mentoree import create_mentoree_task

SERVICE = "techpourtoutes.tasks.create_mentoree.CreateMentoree"


@pytest.mark.django_db
def test_task_loads_beneficiary_and_runs_service(beneficiary):
    with patch(SERVICE) as mock_service:
        mock_service.return_value = MagicMock(
            failure=False, errors=[], failed_with_transient_error=False
        )

        create_mentoree_task(str(beneficiary.pk))

    assert mock_service.call_args.kwargs["beneficiary"].pk == beneficiary.pk


@pytest.mark.django_db
def test_task_raises_runtime_error_on_permanent_failure(beneficiary):
    with patch(SERVICE) as mock_service:
        mock_service.return_value = MagicMock(
            failure=True, errors=["boom"], failed_with_transient_error=False
        )

        with pytest.raises(RuntimeError, match="boom"):
            create_mentoree_task(str(beneficiary.pk))


@pytest.mark.django_db
def test_task_raises_transient_error_on_transient_failure(beneficiary):
    with patch(SERVICE) as mock_service:
        mock_service.return_value = MagicMock(
            failure=True, errors=["boom"], failed_with_transient_error=True
        )

        with pytest.raises(TransientError, match="boom"):
            create_mentoree_task(str(beneficiary.pk))
