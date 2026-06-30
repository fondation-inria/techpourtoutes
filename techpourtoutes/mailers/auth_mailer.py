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
        cls.send_mail(
            subject="Votre lien de connexion à TechPourToutes",
            recipient_list=[user.email],
            context={"user": user, "login_url": f"{settings.SITE_URL}{path}"},
            tags=["utilisateur", "mail de connexion"],
        )
