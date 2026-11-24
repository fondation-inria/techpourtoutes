import httpx

from techpourtoutes.clients.discord import DiscordClient
from techpourtoutes.services.base_api import BaseApiService

HTTP_ERROR_MESSAGE = "Discord n’a pas pu traiter la demande (code {code}). Réessaie plus tard."
NETWORK_ERROR_MESSAGE = "Impossible de joindre Discord. Réessaie plus tard."


class DiscordApiBaseService(BaseApiService):
    """Calls one `DiscordClient` method and fails unless Discord answered with a success, or
    with one of the `tolerated_status_codes` a subclass reads as the outcome it wanted."""

    tolerated_status_codes: frozenset[int] = frozenset()

    def request(self, *, method: str, **kwargs) -> httpx.Response:
        try:
            response = getattr(DiscordClient(), method)(**kwargs)
        except httpx.RequestError:
            self.network_error = True
            self.fail(NETWORK_ERROR_MESSAGE)
        if not response.is_success and response.status_code not in self.tolerated_status_codes:
            self.status_code = response.status_code
            self.fail(HTTP_ERROR_MESSAGE.format(code=response.status_code))
        return response
