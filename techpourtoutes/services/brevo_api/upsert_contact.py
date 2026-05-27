from .base_service import BrevoApiBaseService
from .mappings import brevo_attributes_for, brevo_list_id_for


class UpsertBrevoContact(BrevoApiBaseService):
    def perform(self, *, instance) -> None:
        list_id = brevo_list_id_for(instance)
        attributes = brevo_attributes_for(instance)
        if list_id is None or attributes is None:
            return
        self.request(
            method="upsert_contact",
            ext_id=str(instance.pk),
            list_id=list_id,
            attributes=attributes,
        )
