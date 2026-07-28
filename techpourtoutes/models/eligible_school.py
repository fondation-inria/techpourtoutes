from django.db import models
from django.utils.translation import gettext_lazy as _

from techpourtoutes.text import strip_accents

from .base import BaseModel


class EligibleSchoolManager(models.Manager):
    def record(self, *, uai, name, postal_code, level, matches_digital_domain):
        school, _created = self.get_or_create(
            uai=uai,
            defaults={
                "name": name,
                "postal_code": postal_code,
                "education_level": level,
                "matches_digital_domain": matches_digital_domain,
            },
        )
        school.merge(level=level, matches_digital_domain=matches_digital_domain)
        school.save()
        return school


class EligibleSchool(BaseModel):
    class EducationLevel(models.TextChoices):
        NON_SUP = "non_sup", _("Lycée (pas sup)")
        SUP = "sup", _("Supérieur")
        BOTH = "both", _("Les deux")

    uai = models.CharField(max_length=20, unique=True, verbose_name="UAI")
    name = models.CharField(max_length=255, verbose_name=_("nom de l'établissement"))
    name_normalized = models.CharField(max_length=255, blank=True, editable=False)
    postal_code = models.CharField(max_length=10, blank=True, verbose_name=_("code postal"))
    education_level = models.CharField(max_length=10, choices=EducationLevel.choices)
    matches_digital_domain = models.BooleanField(
        default=False, verbose_name=_("formation numérique/informatique repérée")
    )

    objects = EligibleSchoolManager()

    class Meta:
        verbose_name = _("établissement éligible")
        verbose_name_plural = _("établissements éligibles")

    def save(self, *args, **kwargs):
        self.name_normalized = strip_accents(self.name)
        super().save(*args, **kwargs)

    def merge(self, *, level, matches_digital_domain):
        if level != self.education_level:
            self.education_level = self.EducationLevel.BOTH
        if matches_digital_domain:
            self.matches_digital_domain = True

    def __str__(self):
        return f"{self.name} ({self.postal_code})"
