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

    class Category(models.TextChoices):
        APPS_AND_WEB = "apps_and_web", _("Applis et web")
        GAMES = "games", _("Jeux")
        DATA_AND_AI = "data_and_ai", _("Data et IA")
        OBJECTS_AND_ROBOTICS = "objects_and_robotics", _("Objets et robotique")

    CATEGORY_COLORS = {
        Category.APPS_AND_WEB: "yellow",
        Category.GAMES: "purple",
        Category.DATA_AND_AI: "green",
        Category.OBJECTS_AND_ROBOTICS: "orange",
    }

    title = models.CharField(max_length=255, verbose_name=_("titre"))
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_("slug"))
    category = models.CharField(
        max_length=255, choices=Category.choices, verbose_name=_("catégorie")
    )
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

    @property
    def category_color(self):
        return self.CATEGORY_COLORS[self.category]
