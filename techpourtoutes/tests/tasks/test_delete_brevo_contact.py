from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.tasks._retry import TransientError
from techpourtoutes.tasks.delete_brevo_contact import delete_brevo_contact_task


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_delete_brevo_contact_task_runs_service():
    with patch("techpourtoutes.tasks.delete_brevo_contact.DeleteBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(success=True, failure=False, errors=[])

        delete_brevo_contact_task("abc-123", 42)

        mock_service.assert_called_once_with(ext_id="abc-123", list_id=42)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_delete_brevo_contact_task_raises_runtime_error_on_permanent_failure():
    with patch("techpourtoutes.tasks.delete_brevo_contact.DeleteBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(
            success=False, failure=True, errors=["nope"], status_code=400
        )

        with pytest.raises(RuntimeError, match="nope"):
            delete_brevo_contact_task("abc-123", 42)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_delete_brevo_contact_task_raises_transient_error_on_transient_failure():
    with patch("techpourtoutes.tasks.delete_brevo_contact.DeleteBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(
            success=False, failure=True, errors=["nope"], status_code=500
        )

        with pytest.raises(TransientError, match="nope"):
            delete_brevo_contact_task("abc-123", 42)
