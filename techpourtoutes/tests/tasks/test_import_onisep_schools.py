from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.tasks._retry import TransientError
from techpourtoutes.tasks.import_onisep_schools import import_onisep_schools_task

SERVICE = "techpourtoutes.tasks.import_onisep_schools.ImportSchools"

# Eager mode is on for the whole suite (root conftest), so a task runs inline.
pytestmark = pytest.mark.django_db


def test_the_task_runs_the_import_service():
    with patch(SERVICE) as service:
        service.return_value = MagicMock(
            failure=False, errors=[], failed_with_transient_error=False
        )

        import_onisep_schools_task(scope="secondary", sample=True)

    service.assert_called_once_with(scope="secondary", sample=True)


def test_a_permanent_failure_raises_a_runtime_error():
    with patch(SERVICE) as service:
        service.return_value = MagicMock(
            failure=True, errors=["boum"], failed_with_transient_error=False
        )

        with pytest.raises(RuntimeError, match="boum"):
            import_onisep_schools_task()


def test_a_transient_failure_asks_celery_to_retry():
    with patch(SERVICE) as service:
        service.return_value = MagicMock(
            failure=True, errors=["boum"], failed_with_transient_error=True
        )

        with pytest.raises(TransientError, match="boum"):
            import_onisep_schools_task()
