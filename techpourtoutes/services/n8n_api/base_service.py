import logging

import httpx

from techpourtoutes.services.base import BaseService

logger = logging.getLogger(__name__)

HTTP_ERROR_MESSAGE = "L'appel au webhook n8n a échoué (code {code})."
NETWORK_ERROR_MESSAGE = "Impossible de joindre le webhook n8n."


class N8nApiBaseService(BaseService):
    _network_error: bool = False

    def request(self, path: str, *, payload: dict) -> None:
        try:
            response = httpx.post(path, json=payload, timeout=10)
        except httpx.RequestError:
            self._network_error = True
            self.fail(NETWORK_ERROR_MESSAGE)
            return
        logger.debug(
            f"body={payload} \nresponse={response.text}",
        )

        if not response.is_success:
            self.status_code = response.status_code
            self.fail(HTTP_ERROR_MESSAGE.format(code=response.status_code))

    @property
    def is_transient_failure(self) -> bool:
        if self._network_error:
            return True
        code = getattr(self, "status_code", None)
        if code is None:
            return False
        return code == 429 or code >= 500
