from .base_service import BrevoApiBaseService


class UpsertBrevoContact(BrevoApiBaseService):
    def perform(self, *, ext_id: str | None = None, list_id: int, attributes: dict) -> None:
        self.request(
            method="upsert_contact", ext_id=ext_id, list_id=list_id, attributes=attributes
        )
