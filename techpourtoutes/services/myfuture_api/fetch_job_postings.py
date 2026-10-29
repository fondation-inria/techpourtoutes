from techpourtoutes.utils.myfuture import SUB_DOMAINS

from .base_service import MyFutureApiBaseService

ENDPOINTS = ("offers", "internships")


class FetchMyFutureJobPostings(MyFutureApiBaseService):
    """Both endpoints, every page. They overlap: an offer listed on both comes back once.

    A sample is the first page of the first endpoint: a single call.
    """

    # The API's maximum. It announces no page count, so a shorter page is the last one.
    PAGE_SIZE = 1000

    def perform(self, sample=False) -> None:
        self._records = {}
        for endpoint in ENDPOINTS[:1] if sample else ENDPOINTS:
            self._walk(endpoint, sample=sample)

    def _walk(self, endpoint, *, sample) -> None:
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
            if sample or len(page) < self.PAGE_SIZE:
                return
            offset += self.PAGE_SIZE

    @property
    def myfuture_records(self) -> list:
        return list(getattr(self, "_records", {}).values())
