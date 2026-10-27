from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from techpourtoutes.tasks._retry import TransientError
from techpourtoutes.tasks.subscribe_legal_representative_to_newsletter import (
    subscribe_legal_representative_to_newsletter_task,
)

SERVICE = (
    "techpourtoutes.tasks.subscribe_legal_representative_to_newsletter."
    "SubscribeLegalRepresentativeToNewsletter"
)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_task_subscribes_the_email():
    succeeded = MagicMock(failure=False, errors=[], failed_with_transient_error=False)

    with patch(SERVICE, return_value=succeeded) as subscribe:
        subscribe_legal_representative_to_newsletter_task(email="marie.petit@example.com")

    subscribe.assert_called_once_with(email="marie.petit@example.com")


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_task_raises_a_transient_failure_so_celery_retries():
    failed = MagicMock(failure=True, errors=["429"], failed_with_transient_error=True)

    with patch(SERVICE, return_value=failed), pytest.raises(TransientError):
        subscribe_legal_representative_to_newsletter_task(email="marie.petit@example.com")
