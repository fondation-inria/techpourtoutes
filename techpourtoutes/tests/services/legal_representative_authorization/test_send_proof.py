import pytest
from django.core import mail

from techpourtoutes.services.legal_representative_authorization.send_proof import (
    SendLegalRepresentativeAuthorizationProof,
)


@pytest.mark.django_db
def test_send_proof_builds_the_pdf_first(signed_authorization):
    SendLegalRepresentativeAuthorizationProof(authorization=signed_authorization)

    signed_authorization.refresh_from_db()
    assert signed_authorization.proof_pdf
    assert signed_authorization.proof_pdf_hash


@pytest.mark.django_db
def test_send_proof_mails_the_pdf_to_the_signatory_and_tells_the_beneficiary(
    signed_authorization,
):
    SendLegalRepresentativeAuthorizationProof(authorization=signed_authorization)

    to_signatory, to_beneficiary = mail.outbox
    assert to_signatory.to == ["marie.petit@example.com"]
    assert to_signatory.attachments[0][1].startswith(b"%PDF")
    assert to_beneficiary.to == ["jade@example.com"]
    assert to_beneficiary.subject.startswith("Marie Dupont a signé l'autorisation")
