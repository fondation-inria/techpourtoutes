from celery import shared_task

from techpourtoutes.models import LegalRepresentativeAuthorization
from techpourtoutes.services.legal_representative_authorization.send_proof import (
    SendLegalRepresentativeAuthorizationProof,
)


@shared_task
def send_legal_representative_authorization_proof_task(authorization_pk: str):
    authorization = LegalRepresentativeAuthorization.objects.select_related("beneficiary").get(
        pk=authorization_pk
    )
    SendLegalRepresentativeAuthorizationProof(authorization=authorization)
