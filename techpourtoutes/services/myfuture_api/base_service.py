import httpx

from techpourtoutes.clients.myfuture import MyFutureClient
from techpourtoutes.services.base_api import BaseApiService

HTTP_ERROR_MESSAGE = "La lecture des offres MyFuture a échoué (code {code})."
NETWORK_ERROR_MESSAGE = "Impossible de joindre l'API MyFuture."
PAYLOAD_ERROR_MESSAGE = "La réponse MyFuture n'est pas un JSON exploitable."


class MyFutureApiBaseService(BaseApiService):
    """The offers are paginated: `request` hands the page back to its caller."""

    def request(self, *, method: str, **kwargs) -> list:
        try:
            response = getattr(MyFutureClient(), method)(**kwargs)
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
