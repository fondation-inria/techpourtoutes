from django.conf import settings

from techpourtoutes.services.base import BaseService
from techpourtoutes.services.brevo_api.fetch_contact import FetchBrevoContact
from techpourtoutes.services.brevo_api.mappings import brevo_attributes_for_manifeste_signatory
from techpourtoutes.services.brevo_api.update_contact import UpdateBrevoContact
from techpourtoutes.services.brevo_api.upsert_contact import UpsertBrevoContact


class UpsertManifesteSignatory(BaseService):
    def perform(self, *, first_name, last_name, email, structure_name) -> None:
        if not settings.BREVO_MANIFESTE_LIST_ID:
            return
        attributes = brevo_attributes_for_manifeste_signatory(
            first_name=first_name,
            last_name=last_name,
            email=email,
            structure_name=structure_name,
        )
        if self._contact_exists(email):
            result = UpdateBrevoContact(
                identifier=email,
                identifier_type="email_id",
                list_id=settings.BREVO_MANIFESTE_LIST_ID,
                attributes=attributes,
            )
        else:
            result = UpsertBrevoContact(
                list_id=settings.BREVO_MANIFESTE_LIST_ID, attributes=attributes
            )
        if result.failure:
            self.fail_with_errors(result)

    def _contact_exists(self, email: str) -> bool:
        fetch_result = FetchBrevoContact(identifier=email, identifier_type="email_id")
        if fetch_result.failure and fetch_result.status_code != 404:
            self.fail_with_errors(fetch_result)
        return fetch_result.success
