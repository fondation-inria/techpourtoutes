from django.conf import settings

from techpourtoutes.models.pro import Pro

from .base_mailer import BaseMailer


class AccountMailer(BaseMailer):
    from_email = "TechPourToutes <agir@techpourtoutes.io>"

    @classmethod
    def deletion_confirmation(cls, *, user):
        is_pro = isinstance(user, Pro)
        pronoun = "votre" if is_pro else "ton"
        cls.send_mail(
            subject=f"Confirmation de suppression de {pronoun} compte",
            recipient_list=[user.email],
            context={
                "first_name": user.first_name,
                "is_pro": is_pro,
                "has_jobirl_account": user.jobirl_user_id is not None,
            },
            tags=["utilisateur", "suppression du compte"],
        )

    @classmethod
    def request_external_account_deletion(cls, *, user):
        cls.send_mail(
            subject="Demande de suppression de données personnelles",
            context={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "jobirl_id": user.jobirl_user_id,
            },
            recipient_list=settings.EXTERNAL_ACCOUNT_DELETION_RECIPIENTS,
            tags=["interne", "suppression du compte"],
        )
