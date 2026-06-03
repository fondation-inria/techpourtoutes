import httpx
from django.conf import settings

from techpourtoutes.clients.base import BaseClient


class LatitudesN8nClient(BaseClient):
    """Thin wrapper around the n8n webhook endpoints we call."""

    def __init__(self):
        super().__init__(base_url=settings.N8N_WORKSHOP_WEBHOOK_URL)
        self.auth = self._basic_auth

    def notify_workshop_request(self, *, payload: dict) -> httpx.Response:
        request_kwargs = {"json": payload, "timeout": 10}
        if self.auth is not None:
            request_kwargs["auth"] = self.auth
        return self.post(**request_kwargs)

    @property
    def _basic_auth(self) -> tuple[str, str] | None:
        user = settings.N8N_WORKSHOP_WEBHOOK_BASIC_AUTH_USER
        password = settings.N8N_WORKSHOP_WEBHOOK_BASIC_AUTH_PASSWORD
        if user and password:
            return (user, password)
        return None
