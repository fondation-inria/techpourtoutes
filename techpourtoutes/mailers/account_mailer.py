from .base_mailer import BaseMailer


class AccountMailer(BaseMailer):
    @classmethod
    def delete_account(cls, *, recipient_email, first_name, is_pro, has_jobirl_account=False):
        pronoun = "votre" if is_pro else "ton"
        cls.send_mail(
            subject=f"Confirmation de suppression de {pronoun} compte",
            recipient_list=[recipient_email],
            context={
                "first_name": first_name,
                "is_pro": is_pro,
                "has_jobirl_account": has_jobirl_account,
            },
            tags=["utilisateur", "suppression du compte"],
        )
