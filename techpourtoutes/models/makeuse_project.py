from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..utils.object_storage import public_storage
from .base import BaseModel
from .mixins import SlugFromTitleMixin

# Where the admin's image upload sends the visuals, straight from the browser to the bucket.
IMAGE_PREFIX = "makeuse_projects"


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

    beneficiary = models.ForeignKey(
        "Beneficiary",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="makeuse_projects",
        verbose_name=_("bénéficiaire"),
    )
    title = models.CharField(max_length=255, verbose_name=_("titre"))
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_("slug"))
    category = models.CharField(
        max_length=255, choices=Category.choices, verbose_name=_("catégorie")
    )
    project_type = models.CharField(max_length=255, verbose_name=_("type"))
    creator_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("nom de la créatrice"),
        help_text=_("Laissez vide pour afficher le nom de la bénéficiaire."),
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name=_("adresse mail de contact"),
        help_text=_("Laissez vide pour afficher l'adresse mail de la bénéficiaire."),
    )
    idea = models.TextField(verbose_name=_("mon idée"))
    background = models.TextField(verbose_name=_("mon parcours"))
    methodology = models.TextField(verbose_name=_("ma méthodologie"))
    hobbies = models.TextField(verbose_name=_("mes hobbies"))
    image = models.FileField(
        max_length=255, blank=True, storage=public_storage, verbose_name=_("visuel")
    )
    demo_url = models.URLField(blank=True, verbose_name=_("lien de démo"))

    class Meta:
        verbose_name = _("projet makeuse")
        verbose_name_plural = _("projets makeuses")

    def __str__(self):
        return self.title

    def clean(self):
        """Without a beneficiary to read them from, the name and the email the page displays
        have to be typed."""
        if self.beneficiary_id is None:
            missing = [
                field for field in ("creator_name", "contact_email") if not getattr(self, field)
            ]
            if missing:
                raise ValidationError(
                    {
                        field: _("Renseignez-le, ou liez le projet à une bénéficiaire.")
                        for field in missing
                    }
                )

    @property
    def category_color(self):
        return self.CATEGORY_COLORS[self.category]

    @property
    def creator_label(self):
        return self.creator_name or self.beneficiary.get_full_name()

    @property
    def contact_label(self):
        return self.contact_email or self.beneficiary.email
