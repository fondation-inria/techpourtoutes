import logging

import httpx

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(self, *, base_url: str, headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}

    def post(self, *, path: str, data: dict | None = None) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = httpx.post(url, data=data, headers=self.headers)
        logger.debug(
            f"POST {url} \n"
            f"sent_headers={dict(response.request.headers)} \n"
            f"body={data} \n"
            f"response={response.text}",
        )
        return response
