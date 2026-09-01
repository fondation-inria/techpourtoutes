from .base_service import CarifOrefApiBaseService


class FetchCarifOrefFormations(CarifOrefApiBaseService):
    PAGE_SIZE = 1000

    def perform(self) -> None:
        self._records = []
        page = 1
        while True:
            payload = self.request(method="fetch_formations", page=page, limit=self.PAGE_SIZE)
            self._records += payload["formations"]
            if page >= payload["pagination"]["nombre_de_page"]:
                return
            page += 1

    @property
    def carif_oref_records(self) -> list:
        return getattr(self, "_records", [])
