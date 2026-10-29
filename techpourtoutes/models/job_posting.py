from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models.base import BaseModel


class JobPosting(BaseModel):
    class Category(models.TextChoices):
        HIGHER_ED_INTERNSHIP = "higher_ed_internship", _("Stage du supérieur")
        APPRENTICESHIP = "apprenticeship", _("Alternance")
        SECONDE_INTERNSHIP = "seconde_internship", _("Stage de seconde")
        TROISIEME_INTERNSHIP = "troisieme_internship", _("Stage de troisième")
        FIRST_JOB = "first_job", _("Premier emploi")

    class ContractType(models.TextChoices):
        CDD = "cdd", _("CDD")
        CDI = "cdi", _("CDI")
        INTERIM = "interim", _("Mission d'intérim")
        APPRENTICESHIP = "apprenticeship", _("Contrat d'apprentissage")
        PROFESSIONALIZATION = "professionalization", _("Contrat de professionnalisation")

    class Source(models.TextChoices):
        APEC = "apec", _("Apec")
        MYFUTURE = "myfuture", _("MyFuture")

    source = models.CharField(
        max_length=20, choices=Source.choices, verbose_name=_("source de l'offre")
    )
    external_id = models.CharField(max_length=100, verbose_name=_("identifiant de l'offre"))
    title = models.CharField(max_length=255, verbose_name=_("titre"))
    company_name = models.CharField(max_length=255, verbose_name=_("nom de l'entreprise"))
    description = models.TextField(verbose_name=_("description"))
    postal_code = models.CharField(max_length=10, blank=True, verbose_name=_("code postal"))
    cog_code = models.CharField(max_length=10, blank=True, verbose_name=_("COG"))
    city = models.CharField(max_length=100, verbose_name=_("ville"))
    domains = ArrayField(models.CharField(max_length=255), verbose_name=_("domaines"))
    duration = models.CharField(blank=True, max_length=255, verbose_name=_("durée"))
    company_logo = models.URLField(
        max_length=500, blank=True, verbose_name=_("logo de l'entreprise")
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, verbose_name=_("catégorie")
    )
    contract_type = models.CharField(
        max_length=20, blank=True, choices=ContractType.choices, verbose_name=_("type de contrat")
    )
    published_at = models.DateTimeField(verbose_name=_("publiée le"))
    source_updated_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("mise à jour chez le partenaire le")
    )
    url = models.URLField(verbose_name=_("lien de l'offre"))

    class Meta:
        verbose_name = _("Offre d'emploi")
        verbose_name_plural = _("Offres d'emploi")
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="unique_job_posting_per_source"
            )
        ]

    def __str__(self):
        return self.title
