from http import HTTPStatus

from .base_service import DiscordApiBaseService


class RemoveDiscordGuildMember(DiscordApiBaseService):
    """Has the bot remove her from the server. Discord answers 404 when she already left."""

    tolerated_status_codes = frozenset({HTTPStatus.NOT_FOUND})

    def perform(self, *, user_id):
        self.request(method="remove_guild_member", user_id=user_id)
