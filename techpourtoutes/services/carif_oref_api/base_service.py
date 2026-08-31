import httpx

from techpourtoutes.clients.carif_oref import CarifOrefClient
from techpourtoutes.services.base_api import BaseApiService

HTTP_ERROR_MESSAGE = "La lecture du catalogue Carif-Oref a échoué (code {code})."
NETWORK_ERROR_MESSAGE = "Impossible de joindre le catalogue Carif-Oref."
PAYLOAD_ERROR_MESSAGE = "La réponse Carif-Oref n'est pas un JSON exploitable."


class CarifOrefApiBaseService(BaseApiService):
    """Unlike Onisep, which serves a whole dataset in one file, the catalogue is paginated:
    `request` hands the page back to its caller instead of stashing it."""

    def request(self, *, method: str, **kwargs) -> dict:
        try:
            response = getattr(CarifOrefClient(), method)(**kwargs)
        except httpx.RequestError:
            self.network_error = True
            self.fail(NETWORK_ERROR_MESSAGE)

        if not response.is_success:
            self.status_code = response.status_code
            self.fail(HTTP_ERROR_MESSAGE.format(code=response.status_code))

        try:
            return response.json()
        except ValueError:
            self.fail(PAYLOAD_ERROR_MESSAGE)
