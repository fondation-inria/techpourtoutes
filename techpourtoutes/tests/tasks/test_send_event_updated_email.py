from unittest.mock import patch

import pytest
from django.test import override_settings

from techpourtoutes.tasks.send_event_updated_email import send_event_updated_email_task


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_task_loads_both_sides_and_mails_the_beneficiary(event, beneficiary):
    with patch("techpourtoutes.tasks.send_event_updated_email.BeneficiaryMailer") as mock_mailer:
        send_event_updated_email_task(str(event.pk), str(beneficiary.pk))

    mock_mailer.event_updated.assert_called_once()
    kwargs = mock_mailer.event_updated.call_args.kwargs
    assert kwargs["event"].pk == event.pk
    assert kwargs["beneficiary"].pk == beneficiary.pk
