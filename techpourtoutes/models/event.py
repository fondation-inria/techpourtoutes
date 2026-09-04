from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from .base import BaseModel, BaseQuerySet
from .pro import Pro


class EventQuerySet(BaseQuerySet):
    def approved(self):
        return self.filter(status=Event.Status.APPROVED)

    def past(self):
        return self.filter(end_date__lt=timezone.localdate())

    def upcoming(self):
        """An event that has started but not ended yet is still to come."""
        return self.filter(end_date__gte=timezone.localdate())

    def in_category(self, category):
        return self._within(Event.SUBCATEGORIES[category])

    def in_subcategory(self, subcategory):
        return self._within([subcategory])

    def _within(self, subcategories):
        """`OTHER` also brings back the free text typed when no subcategory fits."""
        match = models.Q(subcategory__in=subcategories)
        if Event.Subcategory.OTHER in subcategories:
            match |= ~models.Q(subcategory__in=Event.Subcategory.values)
        return self.filter(match)


class Event(BaseModel):
    class Category(models.TextChoices):
        INFORMATION = "information", _("Information")
        EMPLOYMENT = "employment", _("Emploi")
        GUIDANCE = "guidance", _("Orientation")
        SOCIAL = "social", _("Convivial")
        CHALLENGE = "challenge", _("Challenge")

    class Subcategory(models.TextChoices):
        CONFERENCE = "conference", _("Conférence")
        WORKSHOP = "workshop", _("Atelier")
        WEBINAR = "webinar", _("Webinaire d'informations")
        ROUND_TABLE = "round_table", _("Table ronde")
        JOB_FAIR = "job_fair", _("Forum de l'emploi")
        SPEED_DATING = "speed_dating", _("Speed dating")
        JOB_DATING = "job_dating", _("Job dating")
        SALON = "salon", _("Salon")
        OPEN_HOUSE = "open_house", _("Portes ouvertes")
        LEARNING_EXPEDITION = "learning_expedition", _("Learning expédition")
        VISIT = "visit", _("Visite")
        JOB_SHADOWING = "job_shadowing", _("Vis-ma-vie")
        AFTERWORK = "afterwork", _("Afterwork")
        CEREMONY = "ceremony", _("Cérémonie")
        HACKATHON = "hackathon", _("Hackathon")
        OTHER = "other", _("Autre")

    SUBCATEGORIES = {
        Category.INFORMATION: (
            Subcategory.CONFERENCE,
            Subcategory.WORKSHOP,
            Subcategory.WEBINAR,
            Subcategory.ROUND_TABLE,
        ),
        Category.EMPLOYMENT: (
            Subcategory.JOB_FAIR,
            Subcategory.SPEED_DATING,
            Subcategory.JOB_DATING,
        ),
        Category.GUIDANCE: (
            Subcategory.SALON,
            Subcategory.OPEN_HOUSE,
            Subcategory.LEARNING_EXPEDITION,
            Subcategory.VISIT,
            Subcategory.JOB_SHADOWING,
        ),
        Category.SOCIAL: (
            Subcategory.AFTERWORK,
            Subcategory.CEREMONY,
            Subcategory.OTHER,
        ),
        Category.CHALLENGE: (Subcategory.HACKATHON,),
    }

    class LocationType(models.TextChoices):
        PHYSICAL = "physical", _("En présentiel")
        ONLINE = "online", _("En ligne")

    class AccessType(models.TextChoices):
        OPEN = "open", _("Sans inscription")
        REGISTRATION = "registration", _("Inscription obligatoire")
        CANDIDACY = "candidacy", _("Sur candidature")

    class Status(models.TextChoices):
        PENDING = "pending", _("En attente de validation")
        APPROVED = "approved", _("Validé")
        REJECTED = "rejected", _("Refusé")

    created_by = models.ForeignKey(
        Pro,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("pro"),
    )
    saved_by = models.ManyToManyField(
        "Beneficiary",
        through="SavedEvent",
        related_name="saved_events",
        verbose_name=_("sauvegardé par"),
    )
    title = models.CharField(verbose_name=_("titre"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    # A `Subcategory` value, or the free text typed when none of them fits.
    subcategory = models.CharField(max_length=100, verbose_name=_("sous-catégorie"))
    start_date = models.DateField(verbose_name=_("date de début"))
    end_date = models.DateField(verbose_name=_("date de fin"))
    start_time = models.TimeField(verbose_name=_("heure de début"))
    end_time = models.TimeField(verbose_name=_("heure de fin"))
    location_type = models.CharField(
        max_length=10, choices=LocationType.choices, verbose_name=_("format")
    )
    # A named place from the Géoplateforme POI index. It holds no street address of its own —
    # the two datasets have no join key — so it stands in for `address` rather than completing it.
    poi_name = models.CharField(max_length=255, blank=True, verbose_name=_("nom du lieu"))
    address = models.CharField(max_length=255, blank=True, verbose_name=_("adresse"))
    postal_code = models.CharField(max_length=10, blank=True, verbose_name=_("code postal"))
    city = models.CharField(max_length=100, blank=True, verbose_name=_("commune"))
    cog_code = models.CharField(max_length=10, blank=True, verbose_name=_("COG de la commune"))
    longitude = models.FloatField(null=True, blank=True, verbose_name=_("longitude"))
    latitude = models.FloatField(null=True, blank=True, verbose_name=_("latitude"))
    ban_id = models.CharField(max_length=30, blank=True, verbose_name=_("identifiant BAN"))
    online_url = models.URLField(blank=True, verbose_name=_("lien de connexion"))
    registration_url = models.URLField(blank=True, verbose_name=_("lien d'inscription"))
    access_type = models.CharField(
        max_length=20, choices=AccessType.choices, verbose_name=_("modalité d'inscription")
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("prix"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("statut"),
    )
    organizer = models.CharField(verbose_name=_("organisateur"))

    objects = EventQuerySet.as_manager()
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("événement")
        verbose_name_plural = _("événements")
        ordering = ["start_date", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F("start_date"))
                | models.Q(end_date=models.F("start_date"), end_time__gte=models.F("start_time")),
                name="event_ends_after_it_starts",
                violation_error_message=_("La fin de l'événement doit suivre son début."),
            ),
            # Literal values: a nested class body cannot see the enclosing class namespace.
            models.CheckConstraint(
                condition=~models.Q(status="approved", location_type="physical")
                | models.Q(latitude__isnull=False, longitude__isnull=False),
                name="approved_physical_event_is_geocoded",
                violation_error_message=_(
                    "Un événement en présentiel doit être géocodé avant d'être validé."
                ),
            ),
            models.CheckConstraint(
                condition=~models.Q(status="approved", location_type="physical")
                | ~models.Q(address="", poi_name=""),
                name="approved_physical_event_names_a_place",
                violation_error_message=_(
                    "Un événement en présentiel doit porter une adresse ou un nom de lieu."
                ),
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def location_label(self):
        """The POI name stands in for the street: it is what people recognise, and a POI
        never comes with one."""
        return " ".join(filter(None, [self.poi_name or self.address, self.postal_code, self.city]))

    @property
    def subcategory_label(self):
        """The free text stands in for the label when the subcategory is not a listed one."""
        if self.subcategory in self.Subcategory.values:
            return self.Subcategory(self.subcategory).label
        return self.subcategory

    @property
    def category(self):
        """Free text is an unlisted subcategory, so it belongs where `OTHER` does."""
        subcategory = self.subcategory
        if subcategory not in self.Subcategory.values:
            subcategory = self.Subcategory.OTHER
        return next(
            category
            for category, subcategories in self.SUBCATEGORIES.items()
            if subcategory in subcategories
        )

    @property
    def category_label(self):
        return self.Category(self.category).label
