from django.db import models
from django.utils.translation import gettext_lazy as _

from techpourtoutes.utils.school_year import (
    current_school_year_start_date,
    next_school_year_start_date,
    school_year_label,
)

from .base import BaseModel
from .formation import Formation
from .level import Level
from .school import School
from .user import User


class TrainingExperience(BaseModel):
    SECONDARY_LEVELS = [Level.TROISIEME, Level.SECONDE, Level.PREMIERE, Level.TERMINALE]
    HIGHER_ED_LEVELS = [
        Level.BAC_1,
        Level.BAC_2,
        Level.BAC_3,
        Level.BAC_4,
        Level.BAC_5,
        Level.BAC_5_PLUS,
    ]
    LEVELS = SECONDARY_LEVELS + HIGHER_ED_LEVELS

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="training_experiences",
        verbose_name=_("utilisateur"),
    )
    school = models.ForeignKey(
        School,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="training_experiences",
        verbose_name=_("établissement"),
    )
    level = models.CharField(
        max_length=20, choices=Level.choices, blank=True, verbose_name=_("niveau")
    )
    formation = models.ForeignKey(
        Formation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="training_experiences",
        verbose_name=_("formation"),
    )
    start_date = models.DateField(null=True, blank=True, verbose_name=_("date de début"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("date de fin"))
    # Superseded by `formation`. Kept until `link_training_experience_formations` has run
    # against a full Onisep catalogue; dropped by the migration that follows.
    course = models.CharField(max_length=255, blank=True, verbose_name=_("filière"))

    class Meta:
        verbose_name = _("formation suivie")
        verbose_name_plural = _("formations suivies")
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "start_date"],
                name="unique_user_start_date",
            )
        ]

    def __str__(self):
        return f"{self.user.email} – {self.formation or ''}"

    @property
    def is_current_school_year(self):
        return self.start_date == current_school_year_start_date()

    @property
    def period_label(self):
        return school_year_label(self.start_date, self.end_date)

    @property
    def period_label_display(self):
        if self.is_current_school_year:
            return _("Année scolaire en cours")
        if self.start_date == next_school_year_start_date():
            return _("L'année prochaine")
        return self.period_label
