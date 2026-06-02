from urllib.parse import urlencode

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Pro


def _base_context():
    return {
        "logo_url": settings.SITE_URL + staticfiles_storage.url("images/techpourtoutes-logo.png"),
        "base_url": settings.SITE_URL,
    }


def _render(template, context=None):
    return render_to_string(template, _base_context() | (context or {}))


class CoalitionMailer:
    @classmethod
    def new_pro(cls, *, pro, engagement):
        recipients = {
            Pro.Engagement.INTERNSHIPS: settings.COALITION_INTERNSHIPS_RECIPIENTS,
            Pro.Engagement.WORK_AMBASSADOR: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
            Pro.Engagement.TRAINING_AMBASSADOR: settings.COALITION_TRAINING_AMBASSADOR_RECIPIENTS,
            Pro.Engagement.SPONSOR: settings.COALITION_SPONSOR_RECIPIENTS,
        }.get(engagement, [])
        context = {"pro": pro, "engagement": Pro.Engagement(engagement).label}
        send_mail(
            subject=f"Une nouvelle demande pour {Pro.Engagement(engagement).label}",
            message=_render("emails/new_pro.txt", context),
            html_message=_render("emails/new_pro.html", context),
            from_email="TechPourToutes <agir@techpourtoutes.io>",
            recipient_list=recipients,
        )

    @classmethod
    def welcome(cls, *, pro, token):
        context = {
            "pro": pro,
            "account_url": f"{settings.SITE_URL}{reverse('login_verify', args=[token])}",
        }
        send_mail(
            subject="Bienvenue dans la Coalition !",
            message=_render("emails/coalition_welcome.txt", context),
            html_message=_render("emails/coalition_welcome.html", context),
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
            message=_render("emails/login_link.txt", context),
            html_message=_render("emails/login_link.html", context),
            from_email="TechPourToutes <noreply@techpourtoutes.io>",
            recipient_list=[user.email],
        )
