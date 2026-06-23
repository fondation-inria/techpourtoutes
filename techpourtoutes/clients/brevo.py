from brevo import Brevo
from brevo.contacts.types.remove_contact_from_list_request_body_ext_ids import (
    RemoveContactFromListRequestBodyExtIds,
)
from django.conf import settings


class BrevoClient:
    """Thin wrapper around the brevo SDK. One method per Brevo endpoint we use.

    Each method returns the raw SDK response (or `None` for void endpoints) so callers
    can read fields like `list_ids`. SDK exceptions (e.g. `brevo.core.api_error.ApiError`)
    bubble up unchanged — failure semantics belong to the service layer.
    """

    def __init__(self):
        self.client = Brevo(api_key=settings.BREVO_API_KEY)

    def upsert_contact(self, *, ext_id: str | None = None, list_id: int, attributes: dict):
        return self.client.contacts.create_contact(
            email=attributes.get("EMAIL"),
            **({"ext_id": ext_id} if ext_id else {}),
            list_ids=[list_id],
            update_enabled=True,
            attributes={k: v for k, v in attributes.items() if k != "EMAIL"},
        )

    def update_contact(
        self, *, identifier: str, identifier_type: str = "ext_id", list_id: int, attributes: dict
    ):
        self.client.contacts.update_contact(
            identifier,
            identifier_type=identifier_type,
            attributes={k: v for k, v in attributes.items() if k != "EMAIL"},
            list_ids=[list_id],
        )

    def delete_contact(self, *, ext_id: str):
        return self.client.contacts.delete_contact(ext_id, identifier_type="ext_id")

    def get_contact(self, *, identifier: str, identifier_type: str = "ext_id"):
        return self.client.contacts.get_contact_info(identifier, identifier_type=identifier_type)

    def remove_contact_from_list(self, *, ext_id: str, list_id: int):
        return self.client.contacts.remove_contact_from_list(
            list_id,
            request=RemoveContactFromListRequestBodyExtIds(ext_ids=[ext_id]),
        )
