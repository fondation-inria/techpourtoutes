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
                "account_url": f"{settings.SITE_URL}{reverse('show_account')}",
            },
            tags=["utilisateur", "beneficiaire", "mail de bienvenue"],
        )

    @classmethod
    def event_updated(cls, *, event, beneficiary):
        cls.send_mail(
            subject=f"L'événement {event.title} a été modifié",
            recipient_list=[beneficiary.email],
            context={
                "event": event,
                "beneficiary": beneficiary,
                "event_url": f"{settings.SITE_URL}{reverse('show_event', args=[event.slug])}",
            },
            tags=["utilisateur", "beneficiaire", "événement modifié"],
        )

    @classmethod
    def makeuse_project_submitted(cls, *, beneficiary):
        cls.send_mail(
            subject="Merci pour ta proposition de projet Makeuse !",
            recipient_list=[beneficiary.email],
            context={"beneficiary": beneficiary},
            tags=["utilisateur", "beneficiaire", "nouvelle proposition de projet Makeuse"],
        )

    @classmethod
    def legal_representative_authorization_signed(cls, *, authorization):
        cls.send_mail(
            subject=(
                f"{authorization.legal_representative_name} a signé l'autorisation pour que tu "
                "puisses bénéficier du programme TechPourToutes"
            ),
            recipient_list=[authorization.beneficiary.email],
            context={"authorization": authorization, "beneficiary": authorization.beneficiary},
            tags=["utilisateur", "beneficiaire", "autorisation signée"],
        )

    @classmethod
    def legal_representative_authorization_reminder(cls, *, authorization):
        cls.send_mail(
            subject=(
                f"{authorization.legal_representative_name} n'a pas encore signé l'autorisation "
                "pour que tu puisses bénéficier du programme TechPourToutes"
            ),
            recipient_list=[authorization.beneficiary.email],
            context={"authorization": authorization, "beneficiary": authorization.beneficiary},
            tags=["utilisateur", "beneficiaire", "relance autorisation"],
        )
