from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .pro import Pro


class WorkshopRequest(BaseModel):
    class Type(models.TextChoices):
        ENQUETE_TECHPOURTOUTES = "enquete_techpourtoutes", _("L'enquête TechPourToutes")
        FUTURE_OF_TECH = "future_of_tech", _("Future of Tech")
        FUTURE_OF_IA = "future_of_ia", _("Future of IA")
        FUTURE_OF_CYBER = "future_of_cyber", _("Future of Cyber")

    pro = models.ForeignKey(
        Pro,
        on_delete=models.CASCADE,
        related_name="workshop_requests",
        verbose_name=_("pro"),
    )
    type = models.CharField(max_length=30, choices=Type.choices, verbose_name=_("type d'atelier"))
    remark = models.TextField(blank=True, verbose_name=_("remarque"))

    class Meta:
        verbose_name = _("demande d'atelier")
        verbose_name_plural = _("demandes d'atelier")

    def __str__(self):
        return f"{self.pro.email} – {self.get_type_display()}"
