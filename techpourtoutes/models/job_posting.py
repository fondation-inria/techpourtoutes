import operator
import re
from functools import reduce
from html import unescape

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    SearchVectorField,
)
from django.db import models
from django.db.models import Case, Q, When
from django.db.models.functions import Coalesce, TruncDate
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from techpourtoutes.models.base import BaseModel, BaseQuerySet

POSTAL_CODE = re.compile(r"\b\d{5}\b")
SEARCH_CONFIG = "french_unaccent"
MASCULINE_OF_FEMININE = (("euse", "eur"), ("trice", "teur"), ("cheffe", "chef"), ("[ée]e", "é"))
LATEST_FIRST = Coalesce("last_updated_at", "published_at").desc()


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

    def with_durations(self, durations):
        """A posting that gives no duration is never left out: it may well last that long."""
        if not durations:
            return self
        ranges = (self.model.DURATION_RANGES[duration] for duration in durations)
        return self.filter(reduce(operator.or_, ranges, Q(duration_months__isnull=True)))

    def with_last_updated_at(self):
        """Annotate `last_updated_at`: the partner's own update date, else ours once the row
        changed on a later day than its creation — only the date is ever shown; null when the
        posting was never updated."""
        updated_by_us = Case(When(~Q(updated_at__date=TruncDate("created_at")), then="updated_at"))
        return self.annotate(last_updated_at=Coalesce("source_updated_at", updated_by_us))

    def latest_first(self):
        """By the date `last_updated_at` shows, else the publication's."""
        return self.with_last_updated_at().order_by(LATEST_FIRST)

    def most_relevant_first(self):
        """After `search()`: ties go to the latest."""
        return self.with_last_updated_at().order_by("-relevance", LATEST_FIRST)

    def search(self, terms):
        query = SearchQuery(
            " & ".join(
                _any_spelling(_masculine(word))
                for word in terms.replace("\x00", "").lower().split()
            ),
            search_type="raw",
            config=SEARCH_CONFIG,
        )
        return self.filter(search_vector=query).annotate(
            relevance=SearchRank(models.F("search_vector"), query)
        )


def _masculine(word):
    for feminine, masculine in MASCULINE_OF_FEMININE:
        word = re.sub(rf"{feminine}(s?)\b", rf"{masculine}\1", word)
    return word


def _any_spelling(word):
    """Matches "node.js" as typed, "nodejs" and "node js", but not "node" and "js" far apart."""
    parts = re.findall(r"\w+", word)
    if len(parts) < 2:
        return _prefix(word)
    spellings = [_prefix(word), _prefix("".join(parts))]
    if all(len(part) > 1 for part in parts):
        spellings.append(" <-> ".join(_prefix(part) for part in parts))
    return "(" + " | ".join(spellings) + ")"


def _prefix(word):
    return "'" + word.replace("\\", "\\\\").replace("'", "''") + "':*"


def _masculine_text(field):
    text = models.F(field)
    for feminine, masculine in MASCULINE_OF_FEMININE:
        text = models.Func(
            text,
            models.Value(rf"{feminine}(s?)\M"),
            models.Value(rf"{masculine}\1"),
            models.Value("gi"),
            function="regexp_replace",
            output_field=models.TextField(),
        )
    return text


class VisibleJobPostingManager(models.Manager.from_queryset(JobPostingQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(hidden=False)


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

    class Duration(models.TextChoices):
        UNDER_3_MONTHS = "under_3_months", _("Moins de 3 mois")
        FROM_3_TO_6_MONTHS = "3_to_6_months", _("De 3 à 6 mois")
        FROM_7_TO_12_MONTHS = "7_to_12_months", _("De 7 à 12 mois")
        OVER_12_MONTHS = "over_12_months", _("Plus de 12 mois")

    class Source(models.TextChoices):
        APEC = "apec", _("Apec")
        MYFUTURE = "myfuture", _("MyFuture")

    objects = VisibleJobPostingManager()
    all_objects = models.Manager()

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

    DURATION_RANGES = {
        Duration.UNDER_3_MONTHS: Q(duration_months__lt=3),
        Duration.FROM_3_TO_6_MONTHS: Q(duration_months__range=(3, 6)),
        Duration.FROM_7_TO_12_MONTHS: Q(duration_months__range=(7, 12)),
        Duration.OVER_12_MONTHS: Q(duration_months__gt=12),
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
    department_code = models.CharField(
        max_length=3, blank=True, db_index=True, verbose_name=_("code du département")
    )
    city = models.CharField(max_length=100, verbose_name=_("ville"))
    street = models.CharField(max_length=255, blank=True, verbose_name=_("adresse"))
    domains = ArrayField(
        models.CharField(max_length=255, choices=Domain.choices), verbose_name=_("domaines")
    )
    duration_months = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("durée (en mois)")
    )
    company_logo = models.URLField(
        max_length=500, blank=True, verbose_name=_("logo de l'entreprise")
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, verbose_name=_("catégorie")
    )
    contract_type = models.CharField(
        max_length=20, blank=True, choices=ContractType.choices, verbose_name=_("type de contrat")
    )
    experience_level = models.CharField(
        max_length=255, blank=True, verbose_name=_("niveau d'expérience")
    )
    salary = models.CharField(max_length=255, blank=True, verbose_name=_("salaire"))
    sector = models.CharField(max_length=255, blank=True, verbose_name=_("secteur"))
    starts_on = models.DateField(null=True, blank=True, verbose_name=_("date de début"))
    ends_on = models.DateField(null=True, blank=True, verbose_name=_("date de fin"))
    published_at = models.DateTimeField(verbose_name=_("publiée le"))
    source_updated_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("mise à jour chez le partenaire le")
    )
    url = models.URLField(verbose_name=_("lien de l'offre"))
    hidden = models.BooleanField(
        default=False,
        verbose_name=_("dépubliée"),
        help_text=_("Une offre dépubliée n'apparaît plus sur le site. Décocher la republie."),
    )
    saved_by = models.ManyToManyField(
        "Beneficiary",
        through="SavedJobPosting",
        related_name="saved_job_postings",
        verbose_name=_("sauvegardée par"),
    )
    clicked_by = models.ManyToManyField(
        "Beneficiary",
        through="ClickedJobPosting",
        related_name="clicked_job_postings",
        verbose_name=_("cliquée par"),
    )
    search_vector = models.GeneratedField(
        expression=SearchVector(_masculine_text("title"), weight="A", config=SEARCH_CONFIG)
        + SearchVector(_masculine_text("company_name"), weight="B", config=SEARCH_CONFIG)
        + SearchVector(_masculine_text("description"), weight="C", config=SEARCH_CONFIG),
        output_field=SearchVectorField(),
        db_persist=True,
    )

    class Meta:
        verbose_name = _("Offre d'emploi")
        verbose_name_plural = _("Offres d'emploi")
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="unique_job_posting_per_source"
            )
        ]
        indexes = [GinIndex(fields=["search_vector"], name="job_posting_search_vector")]

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

    @property
    def address_label(self):
        """Some MyFuture streets already end with a postal code and a city — not always the
        posting's own: a cedex has its own code."""
        locality = f"{self.postal_code} {self.city}".strip()
        if not self.street or POSTAL_CODE.search(self.street):
            return self.street or locality
        return f"{self.street}, {locality}"

    @property
    def description_text(self):
        return unescape(strip_tags(self.description))
