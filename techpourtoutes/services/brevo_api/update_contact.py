from .base_service import BrevoApiBaseService


class UpdateBrevoContact(BrevoApiBaseService):
    def perform(
        self,
        *,
        identifier: str,
        identifier_type: str = "ext_id",
        list_id: int,
        attributes: dict,
    ) -> None:
        self.request(
            method="update_contact",
            identifier=identifier,
            identifier_type=identifier_type,
            list_id=list_id,
            attributes=attributes,
        )
