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

    class Domain(models.TextChoices):
        ELECTRONIQUE = "electronique", _("Électronique")
        ELECTROTECHNIQUE = "electrotechnique", _("Électrotechnique")
        TELECOMMUNICATIONS = "telecommunications", _("Télécommunications")
        TECHNOLOGIES_DE_L_INFORMATION = (
            "technologies_de_l_information",
            _("Technologies de l’information"),
        )
        DEVELOPPEMENT = "developpement", _("Développement - programmation - logiciel")
        INFORMATIQUE_DE_GESTION = "informatique_de_gestion", _("Informatique de gestion")
        INFORMATIQUE_GENERALITES = "informatique_generalites", _("Informatique (généralités)")
        INFORMATIQUE_INDUSTRIELLE = (
            "informatique_industrielle",
            _("Informatique industrielle et technologique"),
        )
        INFORMATIQUE_POUR_LA_RECHERCHE = (
            "informatique_pour_la_recherche",
            _("Informatique pour la recherche"),
        )
        DIRECTION_INFORMATIQUE = "direction_informatique", _("Direction informatique")
        EXPLOITATION_MAINTENANCE = (
            "exploitation_maintenance",
            _("Exploitation, maintenance informatique"),
        )
        MAITRISE_D_OUVRAGE = "maitrise_d_ouvrage", _("Maîtrise d’ouvrage et fonctionnel")
        SYSTEME_RESEAUX_DONNEES = "systeme_reseaux_donnees", _("Système, réseaux, données")
        MATHEMATIQUES = "mathematiques", _("Mathématiques")
        SCIENCES_DE_L_UNIVERS = "sciences_de_l_univers", _("Sciences de l’univers")

    class Source(models.TextChoices):
        APEC = "apec", _("Apec")
        MYFUTURE = "myfuture", _("MyFuture")

    CATEGORY_CONTRACT_TYPES = {
        Category.FIRST_JOB: [ContractType.CDD, ContractType.CDI, ContractType.INTERIM],
        Category.APPRENTICESHIP: [ContractType.APPRENTICESHIP, ContractType.PROFESSIONALIZATION],
    }

    CATEGORY_COLORS = {
        Category.HIGHER_ED_INTERNSHIP: "purple",
        Category.APPRENTICESHIP: "orange",
        Category.SECONDE_INTERNSHIP: "green",
        Category.TROISIEME_INTERNSHIP: "blue",
        Category.FIRST_JOB: "yellow",
    }

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
    domains = ArrayField(
        models.CharField(max_length=255, choices=Domain.choices), verbose_name=_("domaines")
    )
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
        verbose_name = _("offre")
        verbose_name_plural = _("offres")
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="unique_job_posting_per_source"
            )
        ]

    def __str__(self):
        return self.title

    @property
    def category_color(self):
        return self.CATEGORY_COLORS[self.category]
