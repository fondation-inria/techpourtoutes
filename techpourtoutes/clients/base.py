import logging

import httpx

logger = logging.getLogger(__name__)


class BaseClient:
    """Thin HTTP client wrapper around httpx.

    Subclasses configure a `base_url` and default `headers` in their constructor
    (see JobirlClient for an example). HTTP methods (currently `post`) build the full
    URL from `base_url + path`, attach headers, execute the request, and log the
    full request/response at DEBUG level.

    Callers receive the raw `httpx.Response` and are responsible for checking
    `response.is_success` and parsing the body.
    """

    def __init__(self, *, base_url: str, headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}

    def post(self, *, path: str, payload: dict | None = None) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = httpx.post(url, headers=self.headers, data=payload)
        logger.debug(
            f"POST {url} \n"
            f"sent_headers={dict(response.request.headers)} \n"
            f"body={payload} \n"
            f"response={response.text}",
        )
        return response
