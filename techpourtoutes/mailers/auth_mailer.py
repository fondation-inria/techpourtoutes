from .base_mailer import BaseMailer


class AuthMailer(BaseMailer):
    @classmethod
    def login_code(cls, *, user, code):
        is_pro = hasattr(user, "pro")
        pronoun = "Votre" if is_pro else "Ton"
        cls.send_mail(
            subject=f"{pronoun} code de connexion à TechPourToutes",
            recipient_list=[user.email],
            context={"user": user, "code": code, "is_pro": is_pro},
            tags=["utilisateur", "mail de connexion"],
        )

    @classmethod
    def change_email(cls, *, user, code, new_email=None):
        cls.send_mail(
            subject="Confirmez le changement de votre adresse mail",
            recipient_list=[new_email or user.email],
            context={"user": user, "code": code},
            tags=["utilisateur", "changement d'adresse mail"],
        )
