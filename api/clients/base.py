import json
import logging
from datetime import datetime
from pathlib import Path

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class APIError(Exception):
    pass


class BaseClient:
    error_class: type[Exception] = APIError
    http_error_message: str = "API request failed (code {code})."
    network_error_message: str = "API unreachable."
    debug_folder: str = "api_responses"

    def __init__(self, base_url: str, headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}

    def post(
        self,
        path: str,
        data: dict | None = None,
        *,
        debug_context: str | None = None,
    ) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = httpx.post(url, data=data, headers=self.headers)
            if settings.LOCAL:
                self._save_response(url, data, response, debug_context)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("%s returned %s", type(self).__name__, exc.response.status_code)
            raise self.error_class(
                self.http_error_message.format(code=exc.response.status_code)
            ) from exc
        except httpx.RequestError as exc:
            logger.error("%s network error: %s", type(self).__name__, exc)
            raise self.error_class(self.network_error_message) from exc
        try:
            return response.json()
        except ValueError:
            return {}

    def _save_response(self, url, payload, response, debug_context):
        folder = Path(settings.BASE_DIR) / "var" / self.debug_folder
        folder.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        suffix = f"_{debug_context}" if debug_context else ""
        filepath = folder / f"{timestamp}{suffix}.json"
        try:
            body = response.json()
        except Exception:
            body = response.text
        filepath.write_text(
            json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "status_code": response.status_code,
                    "url": url,
                    "request": payload,
                    "response": body,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
