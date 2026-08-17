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
    out_of_scope_school_name = models.CharField(
        max_length=350, blank=True, verbose_name=_("nom de l'établissement hors catalogue")
    )
    out_of_scope_formation_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("nom de la formation hors catalogue")
    )

    class Meta:
        verbose_name = _("formation suivie")
        verbose_name_plural = _("formations suivies")
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "start_date"],
                name="unique_user_start_date",
            ),
            models.CheckConstraint(
                condition=models.Q(school__isnull=False) ^ ~models.Q(out_of_scope_school_name=""),
                name="school_xor_out_of_scope_school_name",
                violation_error_message=_("Renseignez soit un établissement, soit son nom."),
            ),
            models.CheckConstraint(
                condition=models.Q(formation__isnull=False)
                ^ ~models.Q(out_of_scope_formation_name=""),
                name="formation_xor_out_of_scope_formation_name",
                violation_error_message=_("Renseignez soit une formation, soit son nom."),
            ),
        ]

    def __str__(self):
        return f"{self.user.full_name} – {self.school_label} - {self.formation_label}"

    @property
    def school_label(self):
        return self.school.display_label if self.school else self.out_of_scope_school_name

    @property
    def formation_label(self):
        return self.formation.name if self.formation else self.out_of_scope_formation_name

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
