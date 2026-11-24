from django.db import transaction

from ...models import Beneficiary
from ...tasks import remove_discord_guild_member_task
from ..base import BaseService
from ..discord_api.add_guild_member import AddDiscordGuildMember
from ..discord_api.identify_user import IdentifyDiscordUser

ALREADY_LINKED_MESSAGE = "Ce compte Discord est déjà relié à un autre compte Tech pour toutes."


class JoinDiscordServer(BaseService):
    """Adds her to the Discord server with the account she just authorised, and links it to
    hers. Only one Discord account stays in: the one she linked before is removed."""

    def perform(self, *, beneficiary, code, redirect_uri):
        identity = IdentifyDiscordUser(code=code, redirect_uri=redirect_uri)
        if identity.failure:
            self.fail_with_errors(identity)
        if self._linked_to_someone_else(beneficiary, identity.user_id):
            self.fail(ALREADY_LINKED_MESSAGE)
        membership = AddDiscordGuildMember(
            user_id=identity.user_id, access_token=identity.access_token
        )
        if membership.failure:
            self.fail_with_errors(membership)
        self._link(beneficiary, identity.user_id)

    def _linked_to_someone_else(self, beneficiary, discord_user_id):
        return (
            Beneficiary.objects.filter(discord_user_id=discord_user_id)
            .exclude(pk=beneficiary.pk)
            .exists()
        )

    def _link(self, beneficiary, discord_user_id):
        previous_discord_user_id = beneficiary.discord_user_id
        beneficiary.discord_user_id = discord_user_id
        beneficiary.save(update_fields=["discord_user_id"])
        if previous_discord_user_id not in (None, discord_user_id):
            transaction.on_commit(
                lambda: remove_discord_guild_member_task.delay(previous_discord_user_id)
            )
