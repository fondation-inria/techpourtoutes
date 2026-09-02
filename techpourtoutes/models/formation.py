from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from techpourtoutes.utils.text import strip_accents

from .base import BaseModel, BaseQuerySet
from .level import Level
from .school import School


class FormationQuerySet(BaseQuerySet):
    def taught_at(self, school):
        """What the school teaches, its affiliated schools included — everything if none.

        Call it before `search()`: the fallback answers "this school teaches nothing",
        not "nothing matched what was typed".
        """
        scoped = self.filter(
            Q(actions__school=school) | Q(actions__school__parent_onisep_id=school.onisep_id)
        ).distinct()
        return scoped if scoped.exists() else self

    def search(self, query):
        """Narrow down on every token, accent-insensitively."""
        formations = self
        for token in query.split():
            formations = formations.filter(name_normalized__icontains=strip_accents(token))
        return formations

    def secondary(self):
        return self.filter(secondary=True)

    def higher_ed(self):
        return self.filter(higher_ed=True)


class Formation(BaseModel):
    """A diploma or curriculum as referenced by Onisep, independently of where it is taught."""

    onisep_id = models.CharField(max_length=20, unique=True, verbose_name=_("identifiant Onisep"))
    code_nsf = models.CharField(max_length=50, blank=True, verbose_name=_("code NSF"))
    code_scolarite = models.CharField(max_length=20, blank=True, verbose_name=_("code scolarité"))
    type_acronym = models.CharField(
        max_length=50, blank=True, verbose_name=_("sigle du type de formation")
    )
    type_name = models.CharField(
        max_length=100, blank=True, verbose_name=_("libellé du type de formation")
    )
    name = models.CharField(max_length=255, verbose_name=_("libellé de la formation"))
    name_normalized = models.CharField(max_length=255, blank=True, editable=False)
    acronym = models.CharField(max_length=20, blank=True, verbose_name=_("sigle de la formation"))
    duration_in_years = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("durée en années")
    )
    exit_level = models.CharField(
        max_length=20, choices=Level.choices, blank=True, verbose_name=_("niveau de sortie")
    )
    code_rncp = models.CharField(max_length=10, blank=True, verbose_name=_("code RNCP"))
    certification_level = models.CharField(
        max_length=5, blank=True, verbose_name=_("niveau de certification")
    )
    certification_level_name = models.CharField(
        max_length=50, blank=True, verbose_name=_("libellé du niveau de certification")
    )
    domains = ArrayField(
        models.TextField(), default=list, blank=True, verbose_name=_("domaines de formation")
    )
    sub_domains = ArrayField(
        models.TextField(), default=list, blank=True, verbose_name=_("sous-domaines de formation")
    )
    secondary = models.BooleanField(default=False, verbose_name=_("enseignement secondaire"))
    higher_ed = models.BooleanField(default=False, verbose_name=_("enseignement supérieur"))
    schools = models.ManyToManyField(
        School,
        through="FormationAction",
        related_name="formations",
        verbose_name=_("établissements"),
    )
    objects = FormationQuerySet.as_manager()

    class Meta:
        verbose_name = _("formation")
        verbose_name_plural = _("formations")

    def save(self, *args, **kwargs):
        self.name_normalized = strip_accents(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
