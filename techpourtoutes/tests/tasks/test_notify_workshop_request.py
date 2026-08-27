from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.tasks._retry import TransientError
from techpourtoutes.tasks.notify_workshop_request import notify_workshop_request_task


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_task_loads_pro_and_runs_service(pro):
    with patch(
        "techpourtoutes.tasks.notify_workshop_request.NotifyWorkshopRequest"
    ) as mock_service:
        mock_service.return_value = MagicMock(
            failure=False, errors=[], failed_with_transient_error=False
        )

        notify_workshop_request_task(str(pro.pk), ["future_of_tech"], "hello", "0750001A")

        mock_service.assert_called_once()
        kwargs = mock_service.call_args.kwargs
        assert kwargs["pro"].pk == pro.pk
        assert kwargs["ateliers"] == ["future_of_tech"]
        assert kwargs["remark"] == "hello"


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_task_raises_runtime_error_on_permanent_failure(pro):
    with patch(
        "techpourtoutes.tasks.notify_workshop_request.NotifyWorkshopRequest"
    ) as mock_service:
        mock_service.return_value = MagicMock(
            failure=True, errors=["boom"], failed_with_transient_error=False
        )

        with pytest.raises(RuntimeError, match="boom"):
            notify_workshop_request_task(str(pro.pk), ["future_of_tech"], "", "0750001A")


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_task_raises_transient_error_on_transient_failure(pro):
    with patch(
        "techpourtoutes.tasks.notify_workshop_request.NotifyWorkshopRequest"
    ) as mock_service:
        mock_service.return_value = MagicMock(
            failure=True, errors=["boom"], failed_with_transient_error=True
        )

        with pytest.raises(TransientError, match="boom"):
            notify_workshop_request_task(str(pro.pk), ["future_of_tech"], "", "0750001A")
