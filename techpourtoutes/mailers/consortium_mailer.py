from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse

from ..forms.pro_inscription import OTHER
from ..models import Pro
from .base_mailer import BaseMailer

_ENGAGEMENT_LABELS = {**dict(Pro.Engagement.choices), OTHER: "s'engager autrement"}


class ConsortiumMailer(BaseMailer):
    from_email = "TechPourToutes <agir@techpourtoutes.io>"

    @classmethod
    def pro_signed_up(cls, *, pro, engagement, message=""):
        engagement_label = _ENGAGEMENT_LABELS[engagement]
        cls.send_mail(
            subject=f"Une nouvelle demande pour {engagement_label}",
            recipient_list=cls._pro_signed_up_recipients(pro, engagement),
            context={"pro": pro, "engagement": engagement_label, "message": message},
            tags=["interne", "coalition", "nouvelle demande d'engagement"],
        )

    @classmethod
    def training_ambassador_signed_up(cls, *, pro, training_experience):
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
    def training_ambassador_requested(cls, *, beneficiary, topic):
        cls.send_mail(
            subject="Nouvelle demande pour parler à une ambassadrice",
            recipient_list=settings.COALITION_TRAINING_AMBASSADOR_RECIPIENTS,
            context={
                "beneficiary": beneficiary,
                "topic": topic,
            },
            tags=["interne", "coalition", "nouvelle demande de contact avec une ambassadrice"],
        )

    @classmethod
    def event_submitted(cls, *, event):
        admin_url = cls._event_admin_url(event)
        moderator_emails = Pro.event_moderators().values_list("email", flat=True)
        recipient_list = list(dict.fromkeys([*settings.NEW_EVENT_RECIPIENTS, *moderator_emails]))
        cls.send_mail(
            subject=f"Un nouvel événement à valider : {event.title}",
            recipient_list=recipient_list,
            context={"event": event, "admin_url": admin_url},
            tags=["interne", "coalition", "nouvel événement"],
        )

    @classmethod
    def event_updated(cls, *, event):
        admin_url = cls._event_admin_url(event)
        cls.send_mail(
            subject=f"L'événement {event.title} a été modifié",
            recipient_list=settings.NEW_EVENT_RECIPIENTS,
            context={"event": event, "admin_url": admin_url},
            tags=["interne", "coalition", "événement modifié"],
        )

    @classmethod
    def makeuse_project_submitted(
        cls, *, beneficiary, project_name, project_link, project_description
    ):
        cls.send_mail(
            subject="Nouvelle proposition de projet Makeuse",
            recipient_list=settings.MAKEUSE_PROJECT_SUBMISSION_RECIPIENTS,
            context={
                "beneficiary": beneficiary,
                "project_name": project_name,
                "project_link": project_link,
                "project_description": project_description,
            },
            tags=["interne", "coalition", "nouvelle proposition de projet Makeuse"],
        )

    @staticmethod
    def _pro_signed_up_recipients(pro, engagement):
        """Mobilizing her structure, or helping otherwise, goes to the team following her kind of
        structure."""
        if engagement in (Pro.Engagement.MOBILIZE_STRUCTURE, OTHER):
            return {
                Pro.StructureType.ASSOCIATION: settings.COALITION_ASSOCIATION_RECIPIENTS,
                Pro.StructureType.HIGHER_ED: settings.COALITION_TRAINING_AMBASSADOR_RECIPIENTS,
                Pro.StructureType.SCHOOL: settings.COALITION_SCHOOL_RECIPIENTS,
                Pro.StructureType.COMPANY: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
                Pro.StructureType.PUBLIC_INSTITUTION: (
                    settings.COALITION_PUBLIC_INSTITUTION_RECIPIENTS
                ),
                Pro.StructureType.RETIRED: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
                Pro.StructureType.JOBLESS: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
            }.get(pro.structure_type, [])
        return {
            Pro.Engagement.INTERNSHIPS: settings.COALITION_INTERNSHIPS_RECIPIENTS,
            Pro.Engagement.WORK_AMBASSADOR: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
            Pro.Engagement.SPONSOR: settings.COALITION_SPONSOR_RECIPIENTS,
        }.get(engagement, [])

    @staticmethod
    def _event_admin_url(event):
        """Moderators sign in through the user login, never the admin's: the link goes through
        it, and on to the event once signed in."""
        next_url = reverse("admin:techpourtoutes_event_change", args=[event.pk])
        return f"{settings.SITE_URL}{reverse('login_request')}?{urlencode({'next': next_url})}"
