import pytest
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
def test_beneficiary_welcome_sends_email(beneficiary):
    BeneficiaryMailer.welcome(beneficiary=beneficiary)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [beneficiary.email]
    assert message.subject == "Bienvenue au club"
    assert message.from_email == "TechPourToutes <bonjour@techpourtoutes.io>"
    assert beneficiary.first_name in message.body


@pytest.mark.django_db
def test_beneficiary_welcome_attaches_its_brevo_tags(beneficiary):
    BeneficiaryMailer.welcome(beneficiary=beneficiary)

    assert mail.outbox[0].tags == ["utilisateur", "beneficiaire", "mail de bienvenue"]


@pytest.mark.django_db
@override_settings(
    SITE_URL="https://example.test",
)
def test_event_updated_links_to_the_event(event, beneficiary):
    BeneficiaryMailer.event_updated(event=event, beneficiary=beneficiary)

    expected_url = f"https://example.test/evenements/{event.slug}/"
    message = mail.outbox[0]
    assert expected_url in message.body
    assert expected_url in message.alternatives[0][0]


@pytest.mark.django_db
def test_legal_representative_authorization_signed_names_the_signatory(authorization):
    authorization.legal_representative_name = "Marie Dupont"

    BeneficiaryMailer.legal_representative_authorization_signed(authorization=authorization)

    message = mail.outbox[0]
    assert message.to == ["oceane@example.com"]
    assert message.from_email == "TechPourToutes <bonjour@techpourtoutes.io>"
    assert message.subject == (
        "Marie Dupont a signé l'autorisation pour que tu puisses bénéficier du programme "
        "TechPourToutes"
    )
    assert "Bonjour Océane," in message.body


@pytest.mark.django_db
def test_legal_representative_authorization_reminder_names_the_legal_representative(
    authorization,
):
    BeneficiaryMailer.legal_representative_authorization_reminder(authorization=authorization)

    message = mail.outbox[0]
    assert message.to == ["oceane@example.com"]
    assert message.subject == (
        "Marie Petit n'a pas encore signé l'autorisation pour que tu puisses bénéficier du "
        "programme TechPourToutes"
    )
    assert "Peux-tu en reparler avec Marie Petit" in message.body
