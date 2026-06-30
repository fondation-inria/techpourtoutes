from urllib.parse import urlencode

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import send_mail
from django.core.mail.message import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Pro


class CoalitionInternalMailer:
    @classmethod
    def new_pro(cls, *, pro, engagement):
        recipient_list = {
            Pro.Engagement.INTERNSHIPS: settings.COALITION_INTERNSHIPS_RECIPIENTS,
            Pro.Engagement.WORK_AMBASSADOR: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
            Pro.Engagement.SPONSOR: settings.COALITION_SPONSOR_RECIPIENTS,
        }.get(engagement, [])

        engagement_label = Pro.Engagement(engagement).label if engagement else ""
        context = {"pro": pro, "engagement": engagement_label}
        _deliver_mail(
            recipient_list=recipient_list,
            subject=f"Une nouvelle demande pour {engagement_label}",
            message=_render("emails/new_pro.txt", context),
            html_message=_render("emails/new_pro.html", context),
            template_id=settings.BREVO_TEMPLATE_ID_NEW_PRO,
            params={
                "civility": pro.civility,
                "first_name": pro.first_name,
                "last_name": pro.last_name,
                "email": pro.email,
                "phone": str(pro.phone),
                "structure_name": pro.structure_name,
                "engagement": engagement_label,
            },
        )

    @classmethod
    def new_training_ambassador(cls, *, pro, training_experience):
        engagement_label = Pro.Engagement("training_ambassador").label
        context = {
            "pro": pro,
            "training_experience": training_experience,
            "engagement": engagement_label,
        }
        _deliver_mail(
            recipient_list=settings.COALITION_TRAINING_AMBASSADOR_RECIPIENTS,
            subject=f"Une nouvelle demande pour {engagement_label}",
            message=_render("emails/new_training_ambassador.txt", context),
            html_message=_render("emails/new_training_ambassador.html", context),
            template_id=settings.BREVO_TEMPLATE_ID_NEW_TRAINING_AMBASSADOR,
            params={
                "civility": pro.civility,
                "first_name": pro.first_name,
                "last_name": pro.last_name,
                "email": pro.email,
                "phone": str(pro.phone),
                "engagement": engagement_label,
                "school_name": training_experience.higher_ed_school.full_name,
                "course": training_experience.course,
            },
        )

    @classmethod
    def delete_account_external_request(cls, *, first_name, last_name, jobirl_id):
        recipient_list = settings.COALITION_ACCOUNT_DELETION_RECIPIENTS
        context = {"first_name": first_name, "last_name": last_name, "jobirl_id": jobirl_id}
        send_mail(
            subject="Demande de suppression de données personnelles",
            message=_render("emails/delete_account_external_request.txt", context),
            html_message=_render("emails/delete_account_external_request.html", context),
            from_email="TechPourToutes <agir@techpourtoutes.io>",
            recipient_list=recipient_list,
        )


class CoalitionUserMailer:
    @classmethod
    def new_engagement(cls, *, pro):
        context = {"pro": pro}
        _deliver_mail(
            recipient_list=[pro.email],
            subject="Votre nouvelle demande d'engagement auprès de TechPourToutes",
            message=_render("emails/new_engagement.txt", context),
            html_message=_render("emails/new_engagement.html", context),
            template_id=settings.BREVO_TEMPLATE_ID_NEW_ENGAGEMENT,
            params={"first_name": pro.first_name},
        )

    @classmethod
    def welcome(cls, *, pro, token):
        account_url = f"{settings.SITE_URL}{reverse('login_verify', args=[token])}"
        context = {
            "pro": pro,
            "account_url": account_url,
        }
        _deliver_mail(
            recipient_list=[pro.email],
            subject="Bienvenue dans la Coalition !",
            message=_render("emails/coalition_welcome.txt", context),
            html_message=_render("emails/coalition_welcome.html", context),
            template_id=settings.BREVO_TEMPLATE_ID_WELCOME,
            params={"first_name": pro.first_name, "account_url": account_url},
        )

    @classmethod
    def delete_account(cls, *, recipient_email, first_name, engagements):
        is_mentor = Pro.Engagement.MENTOR in engagements
        context = {"first_name": first_name, "is_mentor": is_mentor}
        send_mail(
            subject="TechPourToutes - Confirmation de suppression de votre compte",
            message=_render("emails/delete_account.txt", context),
            html_message=_render("emails/delete_account.html", context),
            from_email="TechPourToutes <agir@techpourtoutes.io>",
            recipient_list=[recipient_email],
        )


class LoginMailer:
    @classmethod
    def send_link(cls, *, user, token, next_url=""):
        path = reverse("login_verify", args=[token])
        if next_url:
            path = f"{path}?{urlencode({'next': next_url})}"
        login_url = f"{settings.SITE_URL}{path}"
        context = {"user": user, "login_url": login_url}
        _deliver_mail(
            recipient_list=[user.email],
            subject="Votre lien de connexion à TechPourToutes",
            message=_render("emails/login_link.txt", context),
            html_message=_render("emails/login_link.html", context),
            template_id=settings.BREVO_TEMPLATE_ID_LOGIN,
            params={"first_name": user.first_name, "login_url": login_url},
        )


def _base_context():
    return {
        "logo_url": settings.SITE_URL + staticfiles_storage.url("images/techpourtoutes-logo.png"),
        "base_url": settings.SITE_URL,
    }


def _render(template, context=None):
    return render_to_string(template, _base_context() | (context or {}))


def _deliver_mail(
    *,
    recipient_list,
    subject,
    message,
    html_message,
    template_id,
    params,
):
    if settings.EMAIL_BACKEND == "anymail.backends.brevo.EmailBackend":
        mail = EmailMessage(to=recipient_list)
        mail.from_email = None
        mail.template_id = template_id
        mail.merge_global_data = params
        return mail.send()

    return send_mail(
        subject=subject,
        message=message,
        html_message=html_message,
        from_email="TechPourToutes <agir@techpourtoutes.io>",
        recipient_list=recipient_list,
    )
