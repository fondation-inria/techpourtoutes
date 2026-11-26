from .base_service import DiscordApiBaseService


class IdentifyDiscordUser(DiscordApiBaseService):
    """Trades the code Discord handed back for her access token, then reads her Discord id."""

    def perform(self, *, code, redirect_uri):
        token = self.request(method="exchange_code", code=code, redirect_uri=redirect_uri)
        self.access_token = token.json()["access_token"]
        user = self.request(method="fetch_current_user", access_token=self.access_token)
        self.user_id = int(user.json()["id"])
