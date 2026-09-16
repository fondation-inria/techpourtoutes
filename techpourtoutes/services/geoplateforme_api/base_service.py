import httpx

from techpourtoutes.clients.geoplateforme import GeoplateformeClient
from techpourtoutes.services.base_api import BaseApiService

HTTP_ERROR_MESSAGE = "La recherche d'adresse a échoué (code {code})."
NETWORK_ERROR_MESSAGE = "Impossible de joindre le service de géocodage."
PAYLOAD_ERROR_MESSAGE = "La réponse du service de géocodage n'est pas un JSON exploitable."


class GeoplateformeApiBaseService(BaseApiService):
    """Called from within a request/response cycle, so `request` hands the payload straight back
    to its caller rather than stashing it for a later step."""

    def request(self, *, method: str, **kwargs) -> dict:
        try:
            response = getattr(GeoplateformeClient(), method)(**kwargs)
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
