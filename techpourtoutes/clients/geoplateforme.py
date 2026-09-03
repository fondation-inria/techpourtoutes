import httpx

from .base import BaseClient

# The Géoplateforme geocoding service, without an API key. It is the IGN successor of the DINUM
# "API Adresse" and stays backward compatible with its GeoJSON payload.
BASE_URL = "https://data.geopf.fr/geocodage"
SEARCH_TIMEOUT = 5


class GeoplateformeClient(BaseClient):
    def __init__(self):
        super().__init__(base_url=BASE_URL)

    def search_addresses(self, *, query: str, index: str, limit: int) -> httpx.Response:
        return self.get(
            path="search",
            params={
                "q": query,
                "index": index,
                "limit": limit,
                "autocomplete": 1,
            },
            timeout=SEARCH_TIMEOUT,
        )
