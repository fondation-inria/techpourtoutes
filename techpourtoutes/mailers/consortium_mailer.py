from django.conf import settings
from django.urls import reverse

from ..models import Pro
from .base_mailer import BaseMailer


class ConsortiumMailer(BaseMailer):
    from_email = "TechPourToutes <agir@techpourtoutes.io>"

    @classmethod
    def new_pro(cls, *, pro, engagement):
        recipient_list = {
            Pro.Engagement.INTERNSHIPS: settings.COALITION_INTERNSHIPS_RECIPIENTS,
            Pro.Engagement.WORK_AMBASSADOR: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
            Pro.Engagement.SPONSOR: settings.COALITION_SPONSOR_RECIPIENTS,
        }.get(engagement, [])

        engagement_label = Pro.Engagement(engagement).label if engagement else ""
        cls.send_mail(
            subject=f"Une nouvelle demande pour {engagement_label}",
            recipient_list=recipient_list,
            context={"pro": pro, "engagement": engagement_label},
            tags=["interne", "coalition", "nouvelle demande d'engagement"],
        )

    @classmethod
    def new_training_ambassador(cls, *, pro, training_experience):
        engagement_label = Pro.Engagement("training_ambassador").label
        cls.send_mail(
            subject=f"Une nouvelle demande pour {engagement_label}",
            recipient_list=settings.COALITION_TRAINING_AMBASSADOR_RECIPIENTS,
            context={
                "pro": pro,
                "training_experience": training_experience,
                "engagement": engagement_label,
            },
            tags=["interne", "coalition", "nouvelle demande d'engagement"],
        )

    @classmethod
    def new_event(cls, *, event):
        admin_url = settings.SITE_URL + reverse(
            "admin:techpourtoutes_event_change", args=[event.pk]
        )
        cls.send_mail(
            subject=f"Un nouvel événement à valider : {event.title}",
            recipient_list=settings.NEW_EVENT_RECIPIENTS,
            context={"event": event, "admin_url": admin_url},
            tags=["interne", "coalition", "nouvel événement"],
        )

    @classmethod
    def new_mentoring_signup(cls, *, beneficiary, mentoring_signup_data):
        cls.send_mail(
            subject="Nouvelle attestation à envoyer",
            recipient_list=settings.NEW_MENTORING_SIGNUP_RECIPIENTS,
            context={
                "beneficiary": beneficiary,
                "legal_representative_name": mentoring_signup_data.get(
                    "legal_representative_name"
                ),
                "legal_representative_email": mentoring_signup_data.get(
                    "legal_representative_email"
                ),
            },
            tags=["interne", "bénéficiaire", "nouvelle demande de mentorat"],
        )
