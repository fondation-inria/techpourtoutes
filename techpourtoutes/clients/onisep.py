import httpx

from .base import BaseClient

# The Onisep open data platform serves whole datasets as a single file, without an API key.
BASE_URL = "https://api.opendata.onisep.fr/downloads"
DOWNLOAD_TIMEOUT = 180


class OnisepClient(BaseClient):
    def __init__(self):
        super().__init__(base_url=BASE_URL)

    def download_dataset(self, *, dataset_id: str) -> httpx.Response:
        return self.get(path=f"{dataset_id}/{dataset_id}.json", timeout=DOWNLOAD_TIMEOUT)
