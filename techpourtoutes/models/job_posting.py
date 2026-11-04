from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models.base import BaseModel, BaseQuerySet


class JobPostingQuerySet(BaseQuerySet):
    def in_domains(self, domains):
        """No ticked domain means no filter, not an empty list."""
        if not domains:
            return self
        return self.filter(domains__overlap=domains)

    def with_contract_types(self, contract_types):
        if not contract_types:
            return self
        return self.filter(contract_type__in=contract_types)

    def in_departments(self, codes):
        if not codes:
            return self
        return self.filter(department_code__in=codes)


class JobPosting(BaseModel):
    class Category(models.TextChoices):
        HIGHER_ED_INTERNSHIP = "higher_ed_internship", _("Stage dans le supérieur")
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
        BASES_DE_DONNEES = "bases_de_donnees", _("Bases de données")
        DEVELOPPEMENT = "developpement", _("Développement - programmation - logiciel")
        INFORMATIQUE_DE_GESTION = "informatique_de_gestion", _("Informatique de gestion")
        INFORMATIQUE = "informatique", _("Informatique")
        INFORMATIQUE_INDUSTRIELLE = "informatique_industrielle", _("Informatique industrielle")
        INFORMATIQUE_POUR_LA_RECHERCHE = (
            "informatique_pour_la_recherche",
            _("Informatique pour la recherche"),
        )
        SYSTEMES_ET_RESEAUX = "systemes_et_reseaux", _("Systèmes et réseaux")
        MATHEMATIQUES = "mathematiques", _("Mathématiques")
        SCIENCES_DE_L_UNIVERS = "sciences_de_l_univers", _("Sciences de l’univers")
        EXPLOITATION_MAINTENANCE = (
            "exploitation_maintenance",
            _("Exploitation, maintenance informatique"),
        )
        MAITRISE_D_OUVRAGE = "maitrise_d_ouvrage", _("Maîtrise d’ouvrage et fonctionnel")
        CREATION = "creation", _("Création")
        CONCEPTION_RECHERCHE = "conception_recherche", _("Conception, recherche")
        DIRECTION_RECHERCHE_DEVELOPPEMENT = (
            "direction_recherche_developpement",
            _("Direction recherche et développement"),
        )
        PROJETS_SCIENTIFIQUES_TECHNIQUES = (
            "projets_scientifiques_techniques",
            _("Projets scientifiques et techniques"),
        )
        TEST_ESSAI_VALIDATION_EXPERTISE = (
            "test_essai_validation_expertise",
            _("Test, essai, validation, expertise"),
        )

    class Source(models.TextChoices):
        APEC = "apec", _("Apec")
        MYFUTURE = "myfuture", _("MyFuture")

    CATEGORY_CONTRACT_TYPES = {
        Category.FIRST_JOB: [ContractType.CDD, ContractType.CDI, ContractType.INTERIM],
        Category.APPRENTICESHIP: [ContractType.APPRENTICESHIP, ContractType.PROFESSIONALIZATION],
    }

    # Only Apec's offers, all of them for graduates, fall in these: pupils are never offered them.
    APEC_DOMAINS = [
        Domain.EXPLOITATION_MAINTENANCE,
        Domain.MAITRISE_D_OUVRAGE,
        Domain.CREATION,
        Domain.CONCEPTION_RECHERCHE,
        Domain.DIRECTION_RECHERCHE_DEVELOPPEMENT,
        Domain.PROJETS_SCIENTIFIQUES_TECHNIQUES,
        Domain.TEST_ESSAI_VALIDATION_EXPERTISE,
    ]
    PUPIL_CATEGORIES = [Category.SECONDE_INTERNSHIP, Category.TROISIEME_INTERNSHIP]

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
    department_code = models.CharField(
        max_length=3, blank=True, db_index=True, verbose_name=_("code du département")
    )
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

    objects = JobPostingQuerySet.as_manager()

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

    @classmethod
    def domains_for(cls, category):
        if category in cls.PUPIL_CATEGORIES:
            return [domain for domain in cls.Domain if domain not in cls.APEC_DOMAINS]
        return list(cls.Domain)

    @property
    def category_color(self):
        return self.CATEGORY_COLORS[self.category]

    @property
    def domain_labels(self):
        return [self.Domain(domain).label for domain in self.domains]
