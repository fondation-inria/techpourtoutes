from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .higher_ed_school import HigherEdSchool
from .pro import Pro


class TrainingExperience(BaseModel):
    pro = models.ForeignKey(
        Pro,
        on_delete=models.CASCADE,
        related_name="training_experiences",
        verbose_name=_("pro"),
    )
    higher_ed_school = models.ForeignKey(
        HigherEdSchool,
        on_delete=models.CASCADE,
        related_name="training_experiences",
        verbose_name=_("établissement d'enseignement supérieur"),
    )
    course = models.CharField(max_length=255, verbose_name=_("cursus"))

    class Meta:
        verbose_name = _("formation")
        verbose_name_plural = _("formations")

    def __str__(self):
        return f"{self.pro.email} – {self.course}"
