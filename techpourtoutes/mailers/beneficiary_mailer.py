from django.conf import settings
from django.urls import reverse

from .base_mailer import BaseMailer


class BeneficiaryMailer(BaseMailer):
    from_email = "TechPourToutes <bonjour@techpourtoutes.io>"

    @classmethod
    def welcome(cls, *, beneficiary):
        cls.send_mail(
            subject="Bienvenue au club",
            recipient_list=[beneficiary.email],
            context={
                "beneficiary": beneficiary,
                "booking_url": settings.BENEFICIARY_BOOKING_URL,
                "account_url": f"{settings.SITE_URL}{reverse('account')}",
            },
            tags=["utilisateur", "beneficiaire", "mail de bienvenue"],
        )
