from .base_service import BrevoApiBaseService


class DeleteBrevoContact(BrevoApiBaseService):
    def perform(self, *, ext_id: str, list_id: int) -> None:
        self.request(method="get_contact", ext_id=ext_id)
        if len(self.brevo_response_body.list_ids) > 1:
            self.request(method="remove_contact_from_list", ext_id=ext_id, list_id=list_id)
        else:
            self.request(method="delete_contact", ext_id=ext_id)
