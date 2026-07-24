from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from techpourtoutes.signals import connect_brevo_sync

from .user import User


class Pro(User):
    class Engagement(models.TextChoices):
        MENTOR = "mentor", _("mentorer")
        INTERNSHIPS = "internships", _("accueillir une stagiaire")
        WORK_AMBASSADOR = "work_ambassador", _("pitcher son métier")
        TRAINING_AMBASSADOR = "training_ambassador", _("devenir ambassadrice étudiante")
        SPONSOR = "sponsor", _("devenir mécène")
        WORKSHOPS = "workshops", _("organiser un atelier")

    class ProfessionalSituation(models.TextChoices):
        WORKING = "working", _("En emploi")
        STUDENT = "student", _("En étude")
        RETIRED = "retired", _("À la retraite")
        JOBLESS = "jobless", _("Sans emploi")

    professional_situation = models.CharField(
        max_length=20,
        choices=ProfessionalSituation.choices,
        verbose_name=_("situation professionnelle"),
    )
    structure_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("nom de la structure")
    )
    structure_id = models.CharField(
        max_length=20, blank=True, verbose_name=_("identifiant de la structure")
    )
    job_title = models.CharField(max_length=255, blank=True, verbose_name=_("métier"))
    faveod_id = models.IntegerField(
        null=True, blank=True, unique=True, verbose_name=_("identifiant faveod")
    )
    jobirl_user_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("identifiant utilisateur jobirl")
    )
    jobirl_user_token = models.CharField(
        max_length=128, blank=True, verbose_name=_("token utilisateur jobirl")
    )
    engagements = ArrayField(
        models.CharField(max_length=30, choices=Engagement.choices),
        default=list,
        blank=True,
        verbose_name=_("engagements"),
    )

    class Meta:
        verbose_name = _("pro")
        verbose_name_plural = _("pros")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.set_unusable_password()
        super().save(*args, **kwargs)

    def add_engagement(self, engagement):
        engagement = str(engagement)
        if engagement not in self.engagements:
            self.engagements.append(engagement)

    def soft_delete(self):
        self.phone = ""
        self.faveod_id = None
        self.jobirl_user_id = None
        self.jobirl_user_token = ""
        super().soft_delete()


connect_brevo_sync(Pro)
