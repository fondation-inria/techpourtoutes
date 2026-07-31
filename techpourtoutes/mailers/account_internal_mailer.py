from django.conf import settings

from .base_mailer import BaseMailer


class AccountInternalMailer(BaseMailer):
    from_email = "TechPourToutes <agir@techpourtoutes.io>"

    @classmethod
    def delete_account_request(cls, *, first_name, last_name, jobirl_id):
        cls.send_mail(
            subject="Demande de suppression de données personnelles",
            context={"first_name": first_name, "last_name": last_name, "jobirl_id": jobirl_id},
            recipient_list=settings.ACCOUNT_DELETION_RECIPIENTS,
            tags=["interne", "suppression du compte"],
        )
