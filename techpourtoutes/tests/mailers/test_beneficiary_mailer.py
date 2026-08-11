import pytest
from django.conf import settings
from django.core import mail
from django.test import override_settings

from techpourtoutes.mailers import BeneficiaryMailer
from techpourtoutes.models import Beneficiary


@pytest.fixture
def beneficiary(db):
    return Beneficiary.objects.create(
        username="oceane@example.com",
        email="oceane@example.com",
        first_name="Océane",
        last_name="Durand",
    )


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_beneficiary_welcome_sends_email(beneficiary):
    BeneficiaryMailer.welcome(beneficiary=beneficiary)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [beneficiary.email]
    assert message.subject == "Bienvenue au club"
    assert message.from_email == "TechPourToutes <bonjour@techpourtoutes.io>"
    assert beneficiary.first_name in message.body
    assert settings.BENEFICIARY_BOOKING_URL in message.body
    assert "/mon-compte/" in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_beneficiary_welcome_attaches_its_brevo_tags(beneficiary):
    BeneficiaryMailer.welcome(beneficiary=beneficiary)

    assert mail.outbox[0].tags == ["utilisateur", "beneficiaire", "mail de bienvenue"]
