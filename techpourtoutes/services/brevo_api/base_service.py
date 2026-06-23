from brevo.core.api_error import ApiError

from techpourtoutes.clients.brevo import BrevoClient
from techpourtoutes.services.base import BaseService

HTTP_ERROR_MESSAGE = "L'appel à Brevo a échoué (code {code}). Détails : {detail}"


class BrevoApiBaseService(BaseService):
    """Base class for Brevo contacts-API service objects.

    Subclasses implement `perform(**kwargs)` and call `self.request(method=..., **kwargs)`.
    The dispatcher calls the matching method on a fresh `BrevoClient` and stores the
    response on `self._brevo_response`, exposed read-only via `brevo_response_body`.
    """

    def request(self, *, method: str, **kwargs) -> None:
        try:
            self._brevo_response = getattr(BrevoClient(), method)(**kwargs)
        except ApiError as exc:
            self.status_code = exc.status_code
            self._fail_with_errors(exc)

    @property
    def brevo_response_body(self):
        return getattr(self, "_brevo_response", None)

    def _fail_with_errors(self, exc: ApiError) -> None:
        detail = ""
        if isinstance(exc.body, dict):
            detail = exc.body.get("message", "")
        self.fail(HTTP_ERROR_MESSAGE.format(code=exc.status_code, detail=detail))
