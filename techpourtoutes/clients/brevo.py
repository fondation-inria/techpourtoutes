from brevo import Brevo
from brevo.contacts.types.remove_contact_from_list_request_body_ext_ids import (
    RemoveContactFromListRequestBodyExtIds,
)
from brevo.core.api_error import ApiError
from django.conf import settings


class BrevoClient:
    """Thin wrapper around the brevo SDK. One method per Brevo endpoint we use.

    Each method returns the raw SDK response (or `None` for void endpoints) so callers
    can read fields like `list_ids`. SDK exceptions (e.g. `brevo.core.api_error.ApiError`)
    bubble up unchanged — failure semantics belong to the service layer.
    """

    def __init__(self):
        self.client = Brevo(api_key=settings.BREVO_API_KEY)

    def upsert_contact(self, *, ext_id: str, list_id: int, attributes: dict):
        """Upsert a contact, recovering from Brevo's SMS-uniqueness conflict.

        Brevo rejects a contact whose SMS is already tied to another contact (HTTP 400).
        The SMS is optional metadata, so on that error we drop it and retry once; any
        other error bubbles up unchanged for the service layer to turn into a failure.
        """
        attributes = dict(attributes)
        email = attributes.pop("EMAIL", None)
        try:
            return self._upsert_contact(
                email=email, ext_id=ext_id, list_id=list_id, attributes=attributes
            )
        except ApiError as exc:
            message = exc.body.get("message", "") if isinstance(exc.body, dict) else ""
            if exc.status_code == 400 and "SMS" in message and "already associated" in message:
                attributes.pop("SMS", None)
                return self._upsert_contact(
                    email=email, ext_id=ext_id, list_id=list_id, attributes=attributes
                )
            raise

    def delete_contact(self, *, ext_id: str):
        return self.client.contacts.delete_contact(ext_id, identifier_type="ext_id")

    def get_contact(self, *, ext_id: str):
        return self.client.contacts.get_contact_info(ext_id, identifier_type="ext_id")

    def remove_contact_from_list(self, *, ext_id: str, list_id: int):
        return self.client.contacts.remove_contact_from_list(
            list_id,
            request=RemoveContactFromListRequestBodyExtIds(ext_ids=[ext_id]),
        )

    # -------------------------- private ----------------------------

    def _upsert_contact(self, *, email, ext_id, list_id, attributes):
        return self.client.contacts.create_contact(
            email=email,
            ext_id=ext_id,
            list_ids=[list_id],
            update_enabled=True,
            attributes=attributes,
        )
