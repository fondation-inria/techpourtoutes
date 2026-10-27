import pytest
from django.core import mail
from django.core.files.base import ContentFile

from techpourtoutes.mailers import LegalRepresentativeMailer


@pytest.mark.django_db
def test_authorization_requested_sends_the_personal_link_to_the_legal_representative(
    authorization,
):
    LegalRepresentativeMailer.authorization_requested(authorization=authorization)

    message = mail.outbox[0]
    assert message.to == ["marie.petit@example.com"]
    assert message.from_email == "TechPourToutes <bonjour@techpourtoutes.io>"
    assert message.subject == (
        "Jade Petit souhaite obtenir votre autorisation pour rejoindre le programme TechPourToutes"
    )
    assert authorization.url in message.body
    assert "Lire et signer l'autorisation" in message.alternatives[0].content


@pytest.mark.django_db
def test_authorization_signed_attaches_the_proof_pdf(authorization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    authorization.proof_pdf.save("proof.pdf", ContentFile(b"%PDF-1.4 proof"))

    LegalRepresentativeMailer.authorization_signed(authorization=authorization)

    message = mail.outbox[0]
    assert message.to == ["marie.petit@example.com"]
    assert message.from_email == "TechPourToutes <bonjour@techpourtoutes.io>"
    assert message.subject == "Votre autorisation signée pour Jade Petit"
    assert "permettre à Jade de rejoindre" in message.body
    assert message.attachments == [
        ("autorisation-techpourtoutes.pdf", b"%PDF-1.4 proof", "application/pdf")
    ]
