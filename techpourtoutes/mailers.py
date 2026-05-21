from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse


class MentorMailer:
    @classmethod
    def welcome(cls, *, mentor):
        context = {"mentor": mentor}
        send_mail(
            subject="Bienvenue dans la Coallition !",
            message=render_to_string("emails/mentor_welcome.txt", context),
            html_message=render_to_string("emails/mentor_welcome.html", context),
            from_email="Tech Pour Toutes <agir@techpourtoutes.io>",
            recipient_list=[mentor.email],
        )


class LoginMailer:
    @classmethod
    def send_link(cls, *, user, token, next_url=""):
        path = reverse("login_verify", args=[token])
        if next_url:
            path = f"{path}?{urlencode({'next': next_url})}"
        login_url = f"{settings.SITE_URL}{path}"
        context = {"user": user, "login_url": login_url}
        send_mail(
            subject="Votre lien de connexion à TechPourToutes",
            message=render_to_string("emails/login_link.txt", context),
            html_message=render_to_string("emails/login_link.html", context),
            from_email="Tech Pour Toutes <noreply@techpourtoutes.io>",
            recipient_list=[user.email],
        )
