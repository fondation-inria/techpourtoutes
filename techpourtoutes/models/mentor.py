from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from .user import User


class Mentor(User):
    class ProfessionalSituation(models.TextChoices):
        WORKING = "working", _("En emploi")
        RETIRED = "retired", _("À la retraite")
        JOBLESS = "jobless", _("Sans emploi")
        STUDENT = "student", _("En étude")

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

    class Meta:
        verbose_name = _("mentor")
        verbose_name_plural = _("mentors")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.set_unusable_password()
        super().save(*args, **kwargs)
