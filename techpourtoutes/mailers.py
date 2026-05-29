from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Pro


class CoalitionMailer:
    @classmethod
    def _recipients_for(cls, engagement):
        return {
            Pro.Engagement.INTERNSHIPS: settings.COALITION_INTERNSHIPS_RECIPIENTS,
            Pro.Engagement.WORK_AMBASSADOR: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
            Pro.Engagement.TRAINING_AMBASSADOR: settings.COALITION_TRAINING_AMBASSADOR_RECIPIENTS,
            Pro.Engagement.SPONSOR: settings.COALITION_SPONSOR_RECIPIENTS,
        }.get(engagement, [])

    @classmethod
    def new_pro(cls, *, pro, engagement):
        context = {"pro": pro, "engagement": Pro.Engagement(engagement).label}
        send_mail(
            subject=f"Une nouvelle demande pour {Pro.Engagement(engagement).label}",
            message=render_to_string("emails/new_pro.txt", context),
            html_message=render_to_string("emails/new_pro.html", context),
            from_email="TechPourToutes <agir@techpourtoutes.io>",
            recipient_list=cls._recipients_for(engagement),
        )

    @classmethod
    def welcome(cls, *, pro):
        context = {"pro": pro}
        send_mail(
            subject="Bienvenue dans la Coalition !",
            message=render_to_string("emails/coalition_welcome.txt", context),
            html_message=render_to_string("emails/coalition_welcome.html", context),
            from_email="TechPourToutes <agir@techpourtoutes.io>",
            recipient_list=[pro.email],
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
            from_email="TechPourToutes <noreply@techpourtoutes.io>",
            recipient_list=[user.email],
        )
