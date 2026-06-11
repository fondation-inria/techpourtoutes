from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from techpourtoutes.text import strip_accents

from .base import BaseModel


class HigherEdSchool(BaseModel):
    class Conference(models.TextChoices):
        CGE = "CGE", "CGE"
        CDEFI = "CDEFI", "CDEFI"
        FU = "FU", "FU"

    full_name = models.CharField(max_length=255, verbose_name=_("nom de l'établissement"))
    full_name_normalized = models.CharField(max_length=255, blank=True, editable=False)
    name = models.CharField(max_length=255, blank=True, verbose_name=_("acronyme"))
    name_normalized = models.CharField(max_length=255, blank=True, editable=False)
    siret = models.CharField(max_length=20, blank=True, verbose_name="SIRET")
    uai = models.CharField(max_length=20, blank=True, verbose_name="UAI")
    conferences = ArrayField(
        models.CharField(max_length=10, choices=Conference.choices),
        default=list,
        blank=True,
        verbose_name=_("conférences"),
    )

    class Meta:
        verbose_name = _("établissement d'enseignement supérieur")
        verbose_name_plural = _("établissements d'enseignement supérieur")
        constraints = [
            models.UniqueConstraint(
                fields=["uai", "name"],
                condition=~models.Q(uai=""),
                name="unique_higher_ed_uai_name",
            ),
            models.UniqueConstraint(
                fields=["siret", "name"],
                condition=~models.Q(siret=""),
                name="unique_higher_ed_siret_name",
            ),
        ]

    def save(self, *args, **kwargs):
        self.name_normalized = strip_accents(self.name)
        self.full_name_normalized = strip_accents(self.full_name)
        super().save(*args, **kwargs)

    @property
    def display_label(self):
        return f"{self.name} ({self.full_name})" if self.name else self.full_name

    def __str__(self):
        return self.name or self.full_name
