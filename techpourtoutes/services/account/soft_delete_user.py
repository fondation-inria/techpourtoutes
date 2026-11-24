from django.db import transaction

from techpourtoutes.mailers.account_mailer import AccountMailer
from techpourtoutes.models import Beneficiary, Pro
from techpourtoutes.tasks import remove_discord_guild_member_task

from ..base import BaseService


class SoftDeleteUser(BaseService):
    def perform(self, *, user):
        jobirl_id = user.jobirl_user_id
        AccountMailer.deletion_confirmation(user=user)
        if jobirl_id is not None:
            AccountMailer.request_jobirl_account_deletion(user=user)
        if isinstance(user, Pro) and "workshops" in user.engagements:
            AccountMailer.request_latitudes_account_deletion(user=user)
        if isinstance(user, Beneficiary) and user.discord_user_id is not None:
            self._leave_discord_server(user.discord_user_id)
        user.soft_delete()

    def _leave_discord_server(self, discord_user_id):
        transaction.on_commit(lambda: remove_discord_guild_member_task.delay(discord_user_id))
