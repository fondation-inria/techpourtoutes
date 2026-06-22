from django.conf import settings

from .base_service import BrevoApiBaseService
from .mappings import brevo_attributes_for_manifeste_signatory


class UpsertManifesteSignatory(BrevoApiBaseService):
    """Push a manifeste signatory to Brevo without creating a User.

    Identified by email (used as the external id), upserted into the dedicated
    manifeste list. Does nothing when no manifeste list is configured.
    """

    def perform(self, *, first_name, last_name, email, structure_name) -> None:
        if not settings.BREVO_MANIFESTE_LIST_ID:
            return
        attributes = brevo_attributes_for_manifeste_signatory(
            first_name=first_name,
            last_name=last_name,
            email=email,
            structure_name=structure_name,
        )
        self.request(
            method="upsert_contact",
            ext_id=email,
            list_id=settings.BREVO_MANIFESTE_LIST_ID,
            attributes=attributes,
        )
