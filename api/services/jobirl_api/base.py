from functools import cached_property

import httpx

from api.clients.jobirl import JobirlClient
from api.services.base import BaseService

HTTP_ERROR_MESSAGE = (
    "L'inscription sur la plateforme partenaire a échoué (code {code}). "
    "Veuillez réessayer ou contacter le support."
)
NETWORK_ERROR_MESSAGE = (
    "Impossible de joindre la plateforme partenaire. Veuillez réessayer ultérieurement."
)


class JobirlApiBaseService(BaseService):
    def request(self, *, method: str, path: str, data: dict | None = None) -> None:
        try:
            self._jobirl_response = getattr(JobirlClient(), method)(path=path, data=data)
        except httpx.RequestError:
            self.fail(NETWORK_ERROR_MESSAGE)
            return
        if not self._jobirl_response.is_success:
            self._fail_with_errors()

    @cached_property
    def jobirl_response_body(self) -> dict:
        try:
            return self._jobirl_response.json().get("datas", {})
        except ValueError:
            return {}

    def _fail_with_errors(self) -> None:
        message = HTTP_ERROR_MESSAGE.format(code=self._jobirl_response.status_code)
        if 400 <= self._jobirl_response.status_code < 500:
            detail = self.jobirl_response_body.get("message", "").strip()
            if detail:
                message = f"{message} Détails : {detail}"
        self.fail(message)
