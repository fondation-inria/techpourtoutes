from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.tasks._retry import TransientError
from techpourtoutes.tasks.delete_brevo_contact import delete_brevo_contact_task
from techpourtoutes.tasks.upsert_brevo_contact import upsert_brevo_contact_task


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test", BREVO_PRO_LIST_ID=42)
def test_upsert_brevo_contact_task_loads_subclass_and_runs_service(pro):
    with patch("techpourtoutes.tasks.upsert_brevo_contact.UpsertBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(
            success=True, failure=False, errors=[], is_transient_failure=False
        )

        upsert_brevo_contact_task(str(pro.pk), "techpourtoutes.Pro")

        mock_service.assert_called_once()
        passed_instance = mock_service.call_args.kwargs["instance"]
        assert passed_instance.__class__.__name__ == "Pro"
        assert str(passed_instance.pk) == str(pro.pk)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_upsert_brevo_contact_task_raises_runtime_error_on_permanent_failure(pro):
    with patch("techpourtoutes.tasks.upsert_brevo_contact.UpsertBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(
            success=False, failure=True, errors=["boom"], is_transient_failure=False
        )

        with pytest.raises(RuntimeError, match="boom"):
            upsert_brevo_contact_task(str(pro.pk), "techpourtoutes.Pro")


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_upsert_brevo_contact_task_raises_transient_error_on_transient_failure(pro):
    with patch("techpourtoutes.tasks.upsert_brevo_contact.UpsertBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(
            success=False, failure=True, errors=["boom"], is_transient_failure=True
        )

        with pytest.raises(TransientError, match="boom"):
            upsert_brevo_contact_task(str(pro.pk), "techpourtoutes.Pro")


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_delete_brevo_contact_task_runs_service():
    with patch("techpourtoutes.tasks.delete_brevo_contact.DeleteBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(
            success=True, failure=False, errors=[], is_transient_failure=False
        )

        delete_brevo_contact_task("abc-123", 42)

        mock_service.assert_called_once_with(ext_id="abc-123", list_id=42)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_delete_brevo_contact_task_raises_runtime_error_on_permanent_failure():
    with patch("techpourtoutes.tasks.delete_brevo_contact.DeleteBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(
            success=False, failure=True, errors=["nope"], is_transient_failure=False
        )

        with pytest.raises(RuntimeError, match="nope"):
            delete_brevo_contact_task("abc-123", 42)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_delete_brevo_contact_task_raises_transient_error_on_transient_failure():
    with patch("techpourtoutes.tasks.delete_brevo_contact.DeleteBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(
            success=False, failure=True, errors=["nope"], is_transient_failure=True
        )

        with pytest.raises(TransientError, match="nope"):
            delete_brevo_contact_task("abc-123", 42)
