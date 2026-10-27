from ...mailers import BeneficiaryMailer, LegalRepresentativeMailer
from ..base import BaseService
from .build_proof import BuildLegalRepresentativeAuthorizationProof


class SendLegalRepresentativeAuthorizationProof(BaseService):
    """Once an authorization is signed: mail its PDF to the signatory and tell the beneficiary."""

    def perform(self, *, authorization):
        result = BuildLegalRepresentativeAuthorizationProof(authorization=authorization)
        if result.failure:
            self.fail_with_errors(result)
        LegalRepresentativeMailer.authorization_signed(authorization=authorization)
        BeneficiaryMailer.legal_representative_authorization_signed(authorization=authorization)
