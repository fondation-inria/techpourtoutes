import json

from techpourtoutes.utils.myfuture import SUB_DOMAINS

from .base_service import MyFutureApiBaseService

ENDPOINTS = ("offers", "internships")


class FetchMyFutureJobPostings(MyFutureApiBaseService):
    """Both endpoints, every page, written to `file` one JSON offer per line as each page comes,
    so that memory never holds more than a page. The endpoints overlap: an offer listed on both
    is written once."""

    # The API's maximum. It announces no page count, so a shorter page is the last one.
    PAGE_SIZE = 1000

    def perform(self, *, file) -> None:
        self._file, self._written = file, set()
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
            self._write(page)
            if len(page) < self.PAGE_SIZE:
                return
            offset += self.PAGE_SIZE

    def _write(self, page) -> None:
        for record in page:
            if record["_id"] not in self._written:
                self._written.add(record["_id"])
                self._file.write(json.dumps(record) + "\n")
