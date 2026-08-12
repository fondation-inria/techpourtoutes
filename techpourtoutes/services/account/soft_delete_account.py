from techpourtoutes.mailers.account_mailer import AccountMailer
from techpourtoutes.models import Pro

from ..base import BaseService


class SoftDeleteAccount(BaseService):
    def perform(self, *, user):
        jobirl_id = user.jobirl_user_id
        AccountMailer.deletion_confirmation(user=user)
        if jobirl_id is not None:
            AccountMailer.request_jobirl_account_deletion(user=user)
        if isinstance(user, Pro) and "workshops" in user.engagements:
            AccountMailer.request_latitudes_account_deletion(user=user)
        user.soft_delete()
