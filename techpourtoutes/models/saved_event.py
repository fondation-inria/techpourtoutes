from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel, BaseQuerySet
from .beneficiary import Beneficiary
from .event import Event


class SavedEventQuerySet(BaseQuerySet):
    def toggle(self, event, beneficiary):
        """Put an event aside, or take it back out. True when it is now saved."""
        deleted, _ = self.filter(event=event, beneficiary=beneficiary).delete()
        if deleted:
            return False
        self.create(event=event, beneficiary=beneficiary)
        return True


class SavedEvent(BaseModel):
    """One event a beneficiary put aside."""

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="saves",
        verbose_name=_("événement"),
    )
    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.CASCADE,
        related_name="saves",
        verbose_name=_("bénéficiaire"),
    )

    objects = SavedEventQuerySet.as_manager()

    class Meta:
        verbose_name = _("événement sauvegardé")
        verbose_name_plural = _("événements sauvegardés")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "beneficiary"],
                name="unique_saved_event_per_beneficiary",
            ),
        ]

    def __str__(self):
        return f"{self.beneficiary.full_name} – {self.event.title}"
