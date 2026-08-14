from .base_service import OnisepApiBaseService


class FetchOnisepFormationActions(OnisepApiBaseService):
    """Download the links between formations and schools."""

    DATASETS = {"lycee": "605340ddc19a9", "superieur": "605344579a7d7"}

    def perform(self, *, scope: str) -> None:
        self.request(method="download_dataset", dataset_id=self.DATASETS[scope])
