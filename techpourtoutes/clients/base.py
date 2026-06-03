import logging

import httpx

logger = logging.getLogger(__name__)


class BaseClient:
    """Thin HTTP client wrapper around httpx.

    Subclasses configure a `base_url` and optional default `headers` in their
    constructor. HTTP methods (currently `post`) build the full URL, attach default
    headers, execute the request, and log the full request/response at DEBUG level.

    Callers receive the raw `httpx.Response` and are responsible for checking
    `response.is_success` and parsing the body.
    """

    def __init__(self, *, base_url: str, headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}

    def post(self, *, path: str = "", **request_kwargs) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url
        request_kwargs = {"headers": self.headers, **request_kwargs}
        response = httpx.post(url, **request_kwargs)
        self._log_request_and_response(url=url, response=response, request_kwargs=request_kwargs)
        return response

    def _log_request_and_response(
        self, *, url: str, response: httpx.Response, request_kwargs: dict
    ) -> None:
        logged_request_kwargs = {
            key: value for key, value in request_kwargs.items() if key != "auth"
        }
        logger.debug(
            f"POST {url} \n"
            f"sent_headers={dict(response.request.headers)} \n"
            f"request_kwargs={logged_request_kwargs} \n"
            f"response={response.text}",
        )
