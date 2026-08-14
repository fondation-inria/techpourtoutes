from unittest.mock import patch

import pytest
from django.test import override_settings

from techpourtoutes.models import Beneficiary
from techpourtoutes.tasks.send_beneficiary_welcome_email import (
    send_beneficiary_welcome_email_task,
)


@pytest.fixture
def beneficiary(db):
    return Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_task_loads_beneficiary_and_sends_welcome_email(beneficiary):
    with patch(
        "techpourtoutes.tasks.send_beneficiary_welcome_email.BeneficiaryMailer"
    ) as mock_mailer:
        send_beneficiary_welcome_email_task(str(beneficiary.pk))

        mock_mailer.welcome.assert_called_once()
        assert mock_mailer.welcome.call_args.kwargs["beneficiary"].pk == beneficiary.pk
