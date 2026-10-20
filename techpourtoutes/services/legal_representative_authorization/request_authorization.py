from ...mailers import LegalRepresentativeMailer
from ...models import LegalRepresentativeAuthorization
from ..base import BaseService


class RequestLegalRepresentativeAuthorization(BaseService):
    """Mail the legal representative a minor names a link to sign her authorization.

    A request still pending is replaced, link included: only the latest details can sign.
    """

    def perform(self, *, beneficiary, legal_representative_name, legal_representative_email):
        LegalRepresentativeAuthorization.objects.pending().filter(beneficiary=beneficiary).delete()
        authorization = LegalRepresentativeAuthorization(
            beneficiary=beneficiary,
            legal_representative_name=legal_representative_name,
            legal_representative_email=legal_representative_email,
        )
        authorization.save()
        LegalRepresentativeMailer.authorization_requested(authorization=authorization)
