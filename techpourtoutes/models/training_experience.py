from django.db import models
from django.utils.translation import gettext_lazy as _

from techpourtoutes.utils.school_year import (
    current_school_year_start_date,
    next_school_year_start_date,
    school_year_label,
)

from .base import BaseModel
from .higher_ed_school import HigherEdSchool
from .school import School
from .user import User


class TrainingExperience(BaseModel):
    class Level(models.TextChoices):
        TROISIEME = "troisieme", _("Troisième")
        SECONDE = "seconde", _("Seconde")
        PREMIERE = "premiere", _("Première")
        TERMINALE = "terminale", _("Terminale")
        BAC_1 = "bac_1", _("Bac +1")
        BAC_2 = "bac_2", _("Bac +2")
        BAC_3 = "bac_3", _("Bac +3")
        BAC_4 = "bac_4", _("Bac +4")
        BAC_5 = "bac_5", _("Bac +5")
        BAC_5_PLUS = "bac_5_plus", _("Au-delà de bac +5")

    SECONDARY_LEVELS = [Level.TROISIEME, Level.SECONDE, Level.PREMIERE, Level.TERMINALE]
    HIGHER_ED_LEVELS = [
        Level.BAC_1,
        Level.BAC_2,
        Level.BAC_3,
        Level.BAC_4,
        Level.BAC_5,
        Level.BAC_5_PLUS,
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="training_experiences",
        verbose_name=_("utilisateur"),
    )
    higher_ed_school = models.ForeignKey(
        HigherEdSchool,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="training_experiences",
        verbose_name=_("établissement d'enseignement supérieur"),
    )
    school = models.ForeignKey(
        School,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="training_experiences",
        verbose_name=_("établissement"),
    )
    level = models.CharField(
        max_length=20, choices=Level.choices, blank=True, verbose_name=_("niveau")
    )
    start_date = models.DateField(null=True, blank=True, verbose_name=_("date de début"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("date de fin"))
    course = models.CharField(max_length=255, verbose_name=_("filière"))

    class Meta:
        verbose_name = _("formation")
        verbose_name_plural = _("formations")
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "start_date"],
                name="unique_user_start_date",
            )
        ]

    def __str__(self):
        return f"{self.user.email} – {self.course}"

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


def training_experience_slots(training_experiences):
    """Experiences plus a placeholder (None) for a missing current year, sorted for display."""
    slots = list(training_experiences)
    if not any(experience.is_current_school_year for experience in slots):
        slots.append(None)
    return sorted(slots, key=_slot_start_date, reverse=True)


def training_experience_insertion_anchor(beneficiary, start_date, exclude_pk=None):
    """Id of the slot to insert before an experience with this start date, or None to append."""
    siblings = beneficiary.training_experiences.all()
    if exclude_pk is not None:
        siblings = siblings.exclude(pk=exclude_pk)
    for slot in training_experience_slots(siblings):
        if _slot_start_date(slot) < start_date:
            return slot.pk if slot else "current-year"
    return None


def _slot_start_date(experience):
    return experience.start_date if experience is not None else current_school_year_start_date()
