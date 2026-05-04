from django.conf import settings

from api.clients.base import APIError, BaseClient


class JobirlAPIError(APIError):
    pass


class JobirlClient(BaseClient):
    error_class = JobirlAPIError
    http_error_message = (
        "L'inscription sur la plateforme partenaire a échoué (code {code}). "
        "Veuillez réessayer ou contacter le support."
    )
    network_error_message = (
        "Impossible de joindre la plateforme partenaire. Veuillez réessayer ultérieurement."
    )
    debug_folder = "jobirl_responses"

    def __init__(self):
        super().__init__(
            base_url=f"{settings.JOBIRL_URL}/techpourtoutes/api",
            headers={
                "Authorization": f"Bearer Bearer: {settings.JOBIRL_API_KEY}",
                # jobirl api somehow whitelists some user-agents
                # python-httpx-xxx or python-requests-xxx are not accepted
                "User-Agent": "curl/8.7.1",
            },
        )
