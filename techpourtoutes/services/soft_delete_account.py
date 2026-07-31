from techpourtoutes.mailers.account_internal_mailer import AccountInternalMailer
from techpourtoutes.mailers.account_mailer import AccountMailer
from techpourtoutes.models import Pro

from .base import BaseService


class SoftDeleteAccount(BaseService):
    def perform(self, *, user):
        recipient_email = user.email
        first_name = user.first_name
        last_name = user.last_name
        is_pro = isinstance(user, Pro)
        jobirl_id = user.jobirl_user_id
        user.soft_delete()
        AccountMailer.delete_account(
            recipient_email=recipient_email,
            first_name=first_name,
            is_pro=is_pro,
            has_jobirl_account=jobirl_id is not None,
        )
        if jobirl_id is not None:
            AccountInternalMailer.delete_account_request(
                first_name=first_name, last_name=last_name, jobirl_id=jobirl_id
            )
