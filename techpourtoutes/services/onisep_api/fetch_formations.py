from .base_service import OnisepApiBaseService


class FetchOnisepFormations(OnisepApiBaseService):
    DATASET = "5fa591127f501"

    def perform(self) -> None:
        self.request(method="download_dataset", dataset_id=self.DATASET)
