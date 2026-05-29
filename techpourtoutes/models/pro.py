from django.contrib.postgres.fields import ArrayField
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from techpourtoutes.signals import connect_brevo_sync

from .user import User


class Pro(User):
    class Engagement(models.TextChoices):
        MENTOR = "mentor", _("Mentorer")
        INTERNSHIPS = "internships", _("Accueillir une stagiaire")
        WORK_AMBASSADOR = "work_ambassador", _("Pitcher mon métier")
        TRAINING_AMBASSADOR = "training_ambassador", _("Pitcher ma formation")
        SPONSOR = "sponsor", _("Devenir mécène")

    class ProfessionalSituation(models.TextChoices):
        WORKING = "working", _("En emploi")
        RETIRED = "retired", _("À la retraite")
        JOBLESS = "jobless", _("Sans emploi")
        STUDENT = "student", _("En étude")

    class Civility(models.TextChoices):
        MADAME = "Madame", _("Madame")
        MONSIEUR = "Monsieur", _("Monsieur")

    civility = models.CharField(
        max_length=10, choices=Civility.choices, verbose_name=_("civilité")
    )
    phone = PhoneNumberField(region="FR", verbose_name=_("téléphone"))
    professional_situation = models.CharField(
        max_length=20,
        choices=ProfessionalSituation.choices,
        verbose_name=_("situation professionnelle"),
    )
    structure_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("nom de la structure")
    )
    job_title = models.CharField(max_length=255, verbose_name=_("métier"))
    postal_code = models.CharField(
        max_length=5,
        validators=[RegexValidator(r"^\d{5}$", _("Entrez un code postal valide à 5 chiffres."))],
        verbose_name=_("code postal"),
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


connect_brevo_sync(Pro)
