from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from ...models import LegalRepresentativeAuthorization
from ...signals import legal_representative_authorization_signed
from ...tasks import (
    send_legal_representative_authorization_proof_task,
    subscribe_legal_representative_to_newsletter_task,
)
from ..base import BaseService


class SignLegalRepresentativeAuthorization(BaseService):
    """Record the legal representative's signature, then enqueues a task to send the PDF."""

    def perform(
        self,
        *,
        authorization,
        legal_representative_name,
        relationship,
        newsletter_consent,
        ip_address,
    ):
        with transaction.atomic():
            self.authorization = (
                LegalRepresentativeAuthorization.objects.pending()
                .select_for_update()
                .filter(pk=authorization.pk)
                .first()
            )
            if self.authorization is None:
                self.fail("Ce lien n'est plus valide.")
            self._record_signature(
                legal_representative_name, relationship, newsletter_consent, ip_address
            )
            transaction.on_commit(self._enqueue_follow_ups)

    def _record_signature(
        self, legal_representative_name, relationship, newsletter_consent, ip_address
    ):
        authorization = self.authorization
        authorization.status = LegalRepresentativeAuthorization.Status.SIGNED
        authorization.legal_representative_name = legal_representative_name
        authorization.relationship = relationship
        authorization.newsletter_consent = newsletter_consent
        authorization.ip_address = ip_address or None
        authorization.signed_at = timezone.now()
        authorization.document = render_to_string(
            "legal_representative_authorization/document.txt",
            {"authorization": authorization, "beneficiary": authorization.beneficiary},
        )
        authorization.save()

    def _enqueue_follow_ups(self):
        send_legal_representative_authorization_proof_task.delay(
            authorization_pk=str(self.authorization.pk)
        )
        if self.authorization.newsletter_consent:
            subscribe_legal_representative_to_newsletter_task.delay(
                email=self.authorization.legal_representative_email
            )
        legal_representative_authorization_signed.send(
            sender=LegalRepresentativeAuthorization, authorization=self.authorization
        )
