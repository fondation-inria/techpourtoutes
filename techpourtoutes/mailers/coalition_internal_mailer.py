from django.conf import settings

from ..models import Pro
from .base_mailer import BaseMailer


class CoalitionInternalMailer(BaseMailer):
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
    def delete_account_external_request(cls, *, first_name, last_name, jobirl_id):
        recipient_list = settings.COALITION_ACCOUNT_DELETION_RECIPIENTS
        cls.send_mail(
            subject="Demande de suppression de données personnelles",
            context={"first_name": first_name, "last_name": last_name, "jobirl_id": jobirl_id},
            recipient_list=recipient_list,
            tags=["interne", "coalition", "suppression du compte"],
        )
