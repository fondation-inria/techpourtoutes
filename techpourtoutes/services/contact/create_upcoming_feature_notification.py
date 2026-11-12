from techpourtoutes.services.brevo_api.base_service import BrevoApiBaseService
from techpourtoutes.services.brevo_api.mappings import (
    brevo_attributes_for_upcoming_feature_notification,
)
from techpourtoutes.services.brevo_api.upsert_contact import UpsertBrevoContact


class CreateUpcomingFeatureNotification(BrevoApiBaseService):
    def perform(self, *, email, list_id) -> None:
        if not list_id:
            return
        attributes = brevo_attributes_for_upcoming_feature_notification(email=email)
        result = UpsertBrevoContact(list_id=list_id, attributes=attributes)
        if result.failure:
            self.status_code = getattr(result, "status_code", None)
            self.fail(result.errors[0])
