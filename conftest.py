import pytest


@pytest.fixture(autouse=True)
def use_simple_static_storage(settings):
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.BREVO_API_KEY = "test"
    settings.BREVO_MENTOR_LIST_ID = 42
    settings.BREVO_SYNC_ENABLED = True


@pytest.fixture(autouse=True)
def mock_brevo_sdk():
    from unittest.mock import patch

    with patch("techpourtoutes.clients.brevo.Brevo") as mock:
        yield mock
