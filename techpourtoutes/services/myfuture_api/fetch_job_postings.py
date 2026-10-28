from techpourtoutes.utils.myfuture import SUB_DOMAINS

from .base_service import MyFutureApiBaseService

ENDPOINTS = ("offers", "internships")


class FetchMyFutureJobPostings(MyFutureApiBaseService):
    """Both endpoints, every page. They overlap: an offer listed on both comes back once."""

    # The API's maximum. It announces no page count, so a shorter page is the last one.
    PAGE_SIZE = 1000

    def perform(self) -> None:
        self._records = {}
        for endpoint in ENDPOINTS:
            self._walk(endpoint)

    def _walk(self, endpoint) -> None:
        offset = 0
        while True:
            page = self.request(
                method="fetch_offers",
                endpoint=endpoint,
                sub_domain_keys=SUB_DOMAINS,
                offset=offset,
                limit=self.PAGE_SIZE,
            )
            self._records.update((record["_id"], record) for record in page)
            if len(page) < self.PAGE_SIZE:
                return
            offset += self.PAGE_SIZE

    @property
    def myfuture_records(self) -> list:
        return list(getattr(self, "_records", {}).values())
