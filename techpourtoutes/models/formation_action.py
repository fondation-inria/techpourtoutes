from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .formation import Formation
from .school import School


class FormationActionQuerySet(models.QuerySet):
    def backing_a_parcours(self):
        """The links a parcours relies on: the two paths `taught_at` reaches a formation by."""
        return self.filter(
            Q(formation__training_experiences__school=F("school"))
            | Q(formation__training_experiences__school__onisep_id=F("school__parent_onisep_id"))
        )


class FormationAction(BaseModel):
    """One formation taught in one établissement — Onisep's "action de formation"."""

    onisep_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("identifiant Onisep"),
    )
    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name=_("formation"),
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name=_("établissement"),
    )

    objects = FormationActionQuerySet.as_manager()

    class Meta:
        verbose_name = _("action de formation")
        verbose_name_plural = _("actions de formation")

    def __str__(self):
        return f"{self.formation.name} – {self.school.name}"
