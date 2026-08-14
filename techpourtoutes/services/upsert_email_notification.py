from django.conf import settings

from techpourtoutes.services.brevo_api.base_service import BrevoApiBaseService
from techpourtoutes.services.brevo_api.mappings import brevo_attributes_for_email_notification
from techpourtoutes.services.brevo_api.upsert_contact import UpsertBrevoContact


class UpsertEmailNotification(BrevoApiBaseService):
    def perform(self, *, email) -> None:
        if not settings.BREVO_EMAIL_NOTIFICATION_LIST_ID:
            return
        attributes = brevo_attributes_for_email_notification(email=email)
        result = UpsertBrevoContact(
            list_id=settings.BREVO_EMAIL_NOTIFICATION_LIST_ID, attributes=attributes
        )
        if result.failure:
            self.status_code = getattr(result, "status_code", None)
            self.fail(result.errors[0])
