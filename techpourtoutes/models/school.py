from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from techpourtoutes.utils.text import strip_accents

from .base import BaseModel

# Written by migration 0036, which folded HigherEdSchool into School before the Onisep rows
# existed. These placeholders only live until the first import has been remapped.
LEGACY_PREFIX = "legacy-"


class SchoolQuerySet(models.QuerySet):
    def secondary(self):
        return self.filter(secondary=True)

    def higher_ed(self):
        return self.filter(higher_ed=True)

    def training_ambassador(self):
        return self.filter(training_ambassador_eligible=True)

    def legacy(self):
        """The placeholders the school merge left behind, not yet repointed onto Onisep."""
        return self.filter(onisep_id__startswith=LEGACY_PREFIX)

    def imported(self):
        return self.exclude(onisep_id__startswith=LEGACY_PREFIX)

    def search(self, query, *, match_postal_code=False):
        """Narrow down on every token, accent-insensitively."""
        schools = self
        for token in query.split():
            needle = strip_accents(token)
            matches = Q(name_normalized__icontains=needle) | Q(
                acronym_normalized__icontains=needle
            )
            if match_postal_code:
                matches |= Q(postal_code__startswith=token)
            schools = schools.filter(matches)
        return schools


class School(BaseModel):
    onisep_id = models.CharField(max_length=20, unique=True, verbose_name=_("identifiant Onisep"))
    uai = models.CharField(max_length=20, blank=True, verbose_name="UAI")
    siret = models.CharField(max_length=20, blank=True, verbose_name="SIRET")
    type = models.CharField(max_length=100, blank=True, verbose_name=_("type d'établissement"))
    name = models.CharField(max_length=350, verbose_name=_("nom de l'établissement"))
    name_normalized = models.CharField(max_length=350, blank=True, editable=False)
    acronym = models.CharField(max_length=50, blank=True, verbose_name=_("sigle"))
    acronym_normalized = models.CharField(max_length=50, blank=True, editable=False)
    status = models.CharField(max_length=30, blank=True, verbose_name=_("statut"))
    parent_uai = models.CharField(
        max_length=20, blank=True, verbose_name=_("UAI de l'université de rattachement")
    )
    parent_onisep_id = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        verbose_name=_("identifiant Onisep de l'université de rattachement"),
    )
    mailbox = models.CharField(max_length=30, blank=True, verbose_name=_("boîte postale"))
    address = models.CharField(max_length=255, blank=True, verbose_name=_("adresse"))
    postal_code = models.CharField(max_length=10, blank=True, verbose_name=_("code postal"))
    city = models.CharField(max_length=100, blank=True, verbose_name=_("commune"))
    cog_code = models.CharField(max_length=10, blank=True, verbose_name=_("COG de la commune"))
    cedex = models.CharField(max_length=30, blank=True, verbose_name=_("cedex"))
    phone = PhoneNumberField(blank=True, verbose_name=_("téléphone"))
    borough = models.CharField(max_length=10, blank=True, verbose_name=_("arrondissement"))
    department = models.CharField(max_length=50, blank=True, verbose_name=_("département"))
    academy = models.CharField(max_length=50, blank=True, verbose_name=_("académie"))
    region = models.CharField(max_length=50, blank=True, verbose_name=_("région"))
    region_code = models.CharField(max_length=10, blank=True, verbose_name=_("COG de région"))
    longitude = models.FloatField(null=True, blank=True, verbose_name=_("longitude"))
    latitude = models.FloatField(null=True, blank=True, verbose_name=_("latitude"))
    secondary = models.BooleanField(default=False, verbose_name=_("enseignement secondaire"))
    higher_ed = models.BooleanField(default=False, verbose_name=_("enseignement supérieur"))
    training_ambassador_eligible = models.BooleanField(
        default=False, verbose_name=_("éligible ambassadrice de formation")
    )

    objects = SchoolQuerySet.as_manager()

    class Meta:
        verbose_name = _("établissement")
        verbose_name_plural = _("établissements")

    def save(self, *args, **kwargs):
        self.name_normalized = strip_accents(self.name)
        self.acronym_normalized = strip_accents(self.acronym)
        super().save(*args, **kwargs)

    @property
    def display_label(self):
        return f"{self.acronym} ({self.name})" if self.acronym else self.name

    @property
    def location_label(self):
        return f"{self.name} ({self.postal_code})" if self.postal_code else self.name

    def __str__(self):
        return self.location_label
