from django.conf import settings

from ..base import BaseService
from ..brevo_api.mappings import brevo_attributes_for_legal_representative
from ..brevo_api.upsert_contact import UpsertBrevoContact


class SubscribeLegalRepresentativeToNewsletter(BaseService):
    """Add a legal representative who asked for the news to her own Brevo list."""

    def perform(self, *, email):
        if not settings.BREVO_LEGAL_REPRESENTATIVE_LIST_ID:
            return
        result = UpsertBrevoContact(
            list_id=settings.BREVO_LEGAL_REPRESENTATIVE_LIST_ID,
            attributes=brevo_attributes_for_legal_representative(email=email),
        )
        if result.failure:
            self.fail_with_errors(result)
