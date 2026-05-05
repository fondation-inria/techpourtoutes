import logging

import httpx

logger = logging.getLogger(__name__)


class APIError(Exception):
    pass


class BaseClient:
    error_class: type[Exception] = APIError
    http_error_message: str = "API request failed (code {code})."
    network_error_message: str = "API unreachable."
    debug_folder: str = "api_responses"

    def __init__(self, *, base_url: str, headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}

    def post(self, *, path: str, data: dict | None = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = httpx.post(url, data=data, headers=self.headers)
            logger.debug(
                f"POST {url} \n"
                f"sent_headers={dict(response.request.headers)} \n"
                f"body={data} \n"
                f"response={response.text}",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(f"{type(self).__name__} returned {exc.response.status_code}")
            raise self.error_class(
                self.http_error_message.format(code=exc.response.status_code)
            ) from exc
        except httpx.RequestError as exc:
            logger.error(f"{type(self).__name__} network error: {exc}")
            raise self.error_class(self.network_error_message) from exc
        try:
            return response.json()
        except ValueError:
            return {}
