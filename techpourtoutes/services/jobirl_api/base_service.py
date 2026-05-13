from functools import cached_property

import httpx

from techpourtoutes.clients.jobirl import JobirlClient
from techpourtoutes.services.base import BaseService

HTTP_ERROR_MESSAGE = (
    "L'inscription sur la plateforme partenaire a échoué (code {code}). "
    "Veuillez réessayer ou contacter support@techpourtoutes.io"
)
NETWORK_ERROR_MESSAGE = (
    "Impossible de joindre la plateforme partenaire. Veuillez réessayer ultérieurement."
)


class JobirlApiBaseService(BaseService):
    """Base class for Jobirl API service objects.

    Subclasses must implement `perform(**kwargs)`, which is called automatically on
    instantiation (see BaseService). A typical implementation calls `self.request()`
    with a method, path, and optional payload, then reads data off
    `self.jobirl_response_body`.

    Flow:
        1. `MyService(foo=bar)` → `perform(foo=bar)` is called automatically.
        2. `perform` calls `self.request(method="post", path="some_endpoint", payload={...})`.
        3. On success, `self.jobirl_response_body` exposes the parsed `datas` dict from
           the Jobirl JSON response. On network or HTTP error, `self.fail()` is called,
           which raises `FailedServiceError` and populates `self.errors`.
        4. After instantiation, callers check `service.success` / `service.failure`.
    """

    def request(self, *, method: str, path: str, payload: dict | None = None) -> None:
        try:
            self._jobirl_response = getattr(JobirlClient(), method)(path=path, payload=payload)
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
