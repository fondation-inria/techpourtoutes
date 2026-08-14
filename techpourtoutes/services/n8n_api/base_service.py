import httpx

from techpourtoutes.clients.n8n import LatitudesN8nClient
from techpourtoutes.services.base_api import BaseApiService

HTTP_ERROR_MESSAGE = "L'appel au webhook n8n a échoué (code {code})."
NETWORK_ERROR_MESSAGE = "Impossible de joindre le webhook n8n."


class N8nApiBaseService(BaseApiService):
    def request(self, *, method: str, payload: dict) -> None:
        try:
            response = getattr(LatitudesN8nClient(), method)(payload=payload)
        except httpx.RequestError:
            self.network_error = True
            self.fail(NETWORK_ERROR_MESSAGE)
            return

        if not response.is_success:
            self.status_code = response.status_code
            self.fail(HTTP_ERROR_MESSAGE.format(code=response.status_code))
