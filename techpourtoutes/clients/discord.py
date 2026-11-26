import httpx
from django.conf import settings

from .base import BaseClient

API_URL = "https://discord.com/api/v10"
TIMEOUT = 10


class DiscordClient(BaseClient):
    """Discord's REST API, using three identities: the app trading an OAuth code, the
    member reading her own profile with her token, and the bot managing the server."""

    def __init__(self):
        super().__init__(
            base_url=API_URL,
            headers={"User-Agent": f"DiscordBot ({settings.SITE_URL}, 1.0)"},
        )

    def exchange_code(self, *, code: str, redirect_uri: str) -> httpx.Response:
        return self.post(
            path="oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(settings.DISCORD_CLIENT_ID, settings.DISCORD_CLIENT_SECRET),
            timeout=TIMEOUT,
        )

    def fetch_current_user(self, *, access_token: str) -> httpx.Response:
        return self.get(
            path="users/@me", headers=self._authorized(f"Bearer {access_token}"), timeout=TIMEOUT
        )

    def add_guild_member(self, *, user_id: int, access_token: str) -> httpx.Response:
        return self.put(
            path=self._member_path(user_id),
            json={"access_token": access_token},
            headers=self._as_bot(),
            timeout=TIMEOUT,
        )

    def remove_guild_member(self, *, user_id: int) -> httpx.Response:
        return self.delete(
            path=self._member_path(user_id), headers=self._as_bot(), timeout=TIMEOUT
        )

    def _member_path(self, user_id: int) -> str:
        return f"guilds/{settings.DISCORD_GUILD_ID}/members/{user_id}"

    def _as_bot(self) -> dict:
        return self._authorized(f"Bot {settings.DISCORD_BOT_TOKEN}")

    def _authorized(self, authorization: str) -> dict:
        return {**self.headers, "Authorization": authorization}
