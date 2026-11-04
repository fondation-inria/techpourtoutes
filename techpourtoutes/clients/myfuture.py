import httpx
from django.conf import settings

from .base import BaseClient

# `/offers` and `/internships` take the same parameters and return the same records.
BASE_URL = "https://api.myfutu.re/api"
PAGE_TIMEOUT = 60


class MyFutureClient(BaseClient):
    def __init__(self):
        super().__init__(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {settings.MYFUTURE_API_KEY}"},
        )

    def fetch_offers(
        self, *, endpoint: str, sub_domain_keys, offset: int, limit: int
    ) -> httpx.Response:
        return self.get(
            path=endpoint,
            params={
                "subDomainKeys": ",".join(sub_domain_keys),
                "offset": offset,
                "limit": limit,
            },
            timeout=PAGE_TIMEOUT,
        )
