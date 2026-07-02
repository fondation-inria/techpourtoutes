from techpourtoutes.mailers.coalition_internal_mailer import CoalitionInternalMailer
from techpourtoutes.mailers.coalition_user_mailer import CoalitionUserMailer

from .base import BaseService


class SoftDeleteAccount(BaseService):
    def perform(self, *, user):
        recipient_email = user.email
        first_name = user.first_name
        last_name = user.last_name
        engagements = user.engagements
        jobirl_id = user.jobirl_user_id
        user.soft_delete()
        user.save()
        CoalitionUserMailer.delete_account(
            recipient_email=recipient_email, first_name=first_name, engagements=engagements
        )
        CoalitionInternalMailer.delete_account_request(
            first_name=first_name, last_name=last_name, jobirl_id=jobirl_id
        )
