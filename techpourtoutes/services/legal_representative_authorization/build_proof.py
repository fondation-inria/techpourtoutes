import hashlib

from django.core.files.base import ContentFile

from ...utils.authorization_proof import build_authorization_proof
from ..base import BaseService


class BuildLegalRepresentativeAuthorizationProof(BaseService):
    """Store the PDF of a signed authorization with its hash, so an altered copy shows."""

    def perform(self, *, authorization):
        proof_pdf = build_authorization_proof(authorization)
        authorization.proof_pdf_hash = hashlib.sha256(proof_pdf).hexdigest()
        authorization.proof_pdf.save(f"{authorization.pk}.pdf", ContentFile(proof_pdf), save=False)
        authorization.save()
