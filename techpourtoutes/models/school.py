import unicodedata

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel


class School(BaseModel):
    identifier = models.CharField(
        max_length=20, unique=True, verbose_name=_("identifiant de l'établissement")
    )
    name = models.CharField(max_length=255, verbose_name=_("nom de l'établissement"))
    name_normalized = models.CharField(max_length=255, blank=True, editable=False)
    postal_code = models.CharField(max_length=10, blank=True, verbose_name=_("code postal"))

    class Meta:
        verbose_name = _("établissement")
        verbose_name_plural = _("établissements")

    @staticmethod
    def normalize(text: str) -> str:
        """Strip accents so search is accent-insensitive (e.g. "Lycée" -> "Lycee")."""
        return "".join(
            char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
        )

    def save(self, *args, **kwargs):
        self.name_normalized = self.normalize(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.postal_code})"
