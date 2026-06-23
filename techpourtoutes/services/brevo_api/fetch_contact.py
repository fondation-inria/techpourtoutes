from .base_service import BrevoApiBaseService


class FetchBrevoContact(BrevoApiBaseService):
    def perform(self, *, identifier: str, identifier_type: str = "ext_id") -> None:
        self.request(method="get_contact", identifier=identifier, identifier_type=identifier_type)
