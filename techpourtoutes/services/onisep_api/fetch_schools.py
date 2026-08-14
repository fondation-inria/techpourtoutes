from .base_service import OnisepApiBaseService


class FetchOnisepSchools(OnisepApiBaseService):
    DATASETS = {"secondary": "5fa5816ac6a6e", "higher_ed": "5fa586da5c4b6"}

    def perform(self, *, scope: str) -> None:
        self.request(method="download_dataset", dataset_id=self.DATASETS[scope])
