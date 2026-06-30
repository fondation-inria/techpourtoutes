from django.conf import settings
from django.urls import reverse

from ..models import Pro
from .base_mailer import BaseMailer


class CoalitionUserMailer(BaseMailer):
    from_email = "TechPourToutes <agir@techpourtoutes.io>"

    @classmethod
    def new_engagement(cls, *, pro):
        cls.send_mail(
            subject="Votre nouvelle demande d'engagement auprès de TechPourToutes",
            recipient_list=[pro.email],
            context={"pro": pro},
            tags=["utilisateur", "coalition", "nouvel engagement utilisateur"],
        )

    @classmethod
    def welcome(cls, *, pro, token):
        login_url = f"{settings.SITE_URL}{reverse('login_verify', args=[token])}"
        cls.send_mail(
            subject="Bienvenue dans la Coalition !",
            recipient_list=[pro.email],
            context={"pro": pro, "login_url": login_url},
            tags=["utilisateur", "coalition", "mail de bienvenue"],
        )

    @classmethod
    def delete_account(cls, *, recipient_email, first_name, engagements):
        is_mentor = Pro.Engagement.MENTOR in engagements
        cls.send_mail(
            subject="TechPourToutes - Confirmation de suppression de votre compte",
            context={"first_name": first_name, "is_mentor": is_mentor},
            recipient_list=[recipient_email],
            tags=["utilisateur", "coalition", "suppression du compte"],
        )
