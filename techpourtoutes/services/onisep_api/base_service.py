import httpx

from techpourtoutes.clients.onisep import OnisepClient
from techpourtoutes.services.base_api import BaseApiService

HTTP_ERROR_MESSAGE = "Le téléchargement du jeu de données Onisep a échoué (code {code})."
NETWORK_ERROR_MESSAGE = "Impossible de joindre l'open data Onisep."
PAYLOAD_ERROR_MESSAGE = "La réponse Onisep n'est pas un JSON exploitable."


class OnisepApiBaseService(BaseApiService):
    def request(self, *, method: str, **kwargs) -> None:
        try:
            response = getattr(OnisepClient(), method)(**kwargs)
        except httpx.RequestError:
            self.network_error = True
            self.fail(NETWORK_ERROR_MESSAGE)
            return

        if not response.is_success:
            self.status_code = response.status_code
            self.fail(HTTP_ERROR_MESSAGE.format(code=response.status_code))
            return

        try:
            self._onisep_records = response.json()
        except ValueError:
            self.fail(PAYLOAD_ERROR_MESSAGE)

    @property
    def onisep_records(self) -> list:
        return getattr(self, "_onisep_records", [])
