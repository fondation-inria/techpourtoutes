from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse

from .base_mailer import BaseMailer


class AuthMailer(BaseMailer):
    @classmethod
    def login_link(cls, *, user, token, next_url=""):
        path = reverse("login_verify", args=[token])
        if next_url:
            path = f"{path}?{urlencode({'next': next_url})}"
        is_pro = hasattr(user, "pro")
        pronoun = "Votre" if is_pro else "Ton"
        subject = f"{pronoun} lien de connexion à TechPourToutes"
        cls.send_mail(
            subject=subject,
            recipient_list=[user.email],
            context={"user": user, "login_url": f"{settings.SITE_URL}{path}", "is_pro": is_pro},
            tags=["utilisateur", "mail de connexion"],
        )
