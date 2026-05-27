from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.tasks.delete_brevo_contact import delete_brevo_contact_task
from techpourtoutes.tasks.upsert_brevo_contact import upsert_brevo_contact_task


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test", BREVO_MENTOR_LIST_ID=42)
def test_upsert_brevo_contact_task_loads_subclass_and_runs_service(mentor):
    with patch("techpourtoutes.tasks.upsert_brevo_contact.UpsertBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(success=True, failure=False, errors=[])

        upsert_brevo_contact_task(str(mentor.pk), "techpourtoutes.Mentor")

        mock_service.assert_called_once()
        passed_instance = mock_service.call_args.kwargs["instance"]
        assert passed_instance.__class__.__name__ == "Mentor"
        assert str(passed_instance.pk) == str(mentor.pk)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_upsert_brevo_contact_task_raises_when_service_fails(mentor):
    with patch("techpourtoutes.tasks.upsert_brevo_contact.UpsertBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(success=False, failure=True, errors=["boom"])

        with pytest.raises(RuntimeError, match="boom"):
            upsert_brevo_contact_task(str(mentor.pk), "techpourtoutes.Mentor")


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_delete_brevo_contact_task_runs_service():
    with patch("techpourtoutes.tasks.delete_brevo_contact.DeleteBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(success=True, failure=False, errors=[])

        delete_brevo_contact_task("abc-123", 42)

        mock_service.assert_called_once_with(ext_id="abc-123", list_id=42)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, BREVO_API_KEY="test")
def test_delete_brevo_contact_task_raises_when_service_fails():
    with patch("techpourtoutes.tasks.delete_brevo_contact.DeleteBrevoContact") as mock_service:
        mock_service.return_value = MagicMock(success=False, failure=True, errors=["nope"])

        with pytest.raises(RuntimeError, match="nope"):
            delete_brevo_contact_task("abc-123", 42)
