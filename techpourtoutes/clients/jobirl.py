from django.conf import settings

from techpourtoutes.clients.base import BaseClient


class JobirlClient(BaseClient):
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
