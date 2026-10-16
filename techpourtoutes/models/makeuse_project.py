from pathlib import Path
from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _

from ..utils.object_storage import public_storage
from .base import BaseModel
from .mixins import SlugFromTitleMixin


def image_key(instance, filename):
    """A fresh key per upload: the public bucket overwrites a file of the same name, and tells
    browsers to cache it for a year."""
    return f"makeuse_projects/{uuid4().hex}{Path(filename).suffix}"


class MakeuseProject(SlugFromTitleMixin, BaseModel):
    SLUG_FALLBACK = "projet"

    title = models.CharField(max_length=255, verbose_name=_("titre"))
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_("slug"))
    project_type = models.CharField(max_length=255, verbose_name=_("type"))
    creator_name = models.CharField(max_length=255, verbose_name=_("nom de la créatrice"))
    contact_email = models.EmailField(verbose_name=_("adresse mail de contact"))
    idea = models.TextField(verbose_name=_("mon idée"))
    background = models.TextField(verbose_name=_("mon parcours"))
    methodology = models.TextField(verbose_name=_("ma méthodologie"))
    hobbies = models.TextField(verbose_name=_("mes hobbies"))
    image = models.FileField(
        max_length=255,
        blank=True,
        storage=public_storage,
        upload_to=image_key,
        verbose_name=_("visuel"),
    )
    demo_url = models.URLField(blank=True, verbose_name=_("lien de démo"))

    class Meta:
        verbose_name = _("projet makeuse")
        verbose_name_plural = _("projets makeuses")

    def __str__(self):
        return self.title
