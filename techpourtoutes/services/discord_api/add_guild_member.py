from .base_service import DiscordApiBaseService


class AddDiscordGuildMember(DiscordApiBaseService):
    """Has the bot add her to the server; one already there is left as she is."""

    def perform(self, *, user_id, access_token):
        self.request(method="add_guild_member", user_id=user_id, access_token=access_token)
