from datetime import datetime

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
from django.db import models
from django.template.defaultfilters import floatformat
from django.templatetags.static import static
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from ..utils.full_text_search import search_vector
from ..utils.object_storage import public_storage
from ..utils.structure_type_teams import structure_types_followed_by
from ..utils.territories import department_code
from ..utils.text import strip_accents
from .base import BaseModel, BaseQuerySet
from .mixins import SearchableQuerySetMixin, SlugFromTitleMixin
from .pro import Pro


class EventQuerySet(SearchableQuerySetMixin, BaseQuerySet):
    def approved(self):
        return self.filter(status=Event.Status.APPROVED)

    def pending(self):
        return self.filter(status=Event.Status.PENDING)

    def visible_to(self, user):
        """An event awaiting validation is still a draft: only the pro who submitted it and
        those who moderate it may open it."""
        visible = self.filter(
            models.Q(status=Event.Status.APPROVED)
            | models.Q(status=Event.Status.PENDING, created_by=user.pk)
        )
        if user.is_staff:
            return visible | self.moderated_by(user)
        return visible

    def moderated_by(self, user):
        """A superuser moderates every event; anyone else only those of the pros whose team
        lists her address."""
        if user.is_superuser:
            return self
        return self.filter(created_by__structure_type__in=structure_types_followed_by(user.email))

    def past(self):
        now = timezone.localtime()
        return self.filter(
            models.Q(end_date__lt=now.date())
            | models.Q(end_date=now.date(), end_time__lt=now.time())
        )

    def upcoming(self):
        """An event that has started but not ended yet is still to come."""
        now = timezone.localtime()
        return self.filter(
            models.Q(end_date__gt=now.date())
            | models.Q(end_date=now.date(), end_time__gte=now.time())
        )

    def in_category(self, category):
        return self._within(Event.SUBCATEGORIES[category])

    def in_subcategory(self, subcategory):
        return self._within([subcategory])

    def in_subcategories(self, subcategories):
        if not subcategories:
            return self
        return self._within(subcategories)

    def in_departments(self, codes):
        """An online event happens anywhere, so a department never leaves it out."""
        if not codes:
            return self
        return self.filter(
            models.Q(location_type=Event.LocationType.ONLINE) | models.Q(department_code__in=codes)
        )

    def with_location_types(self, location_types):
        if not location_types:
            return self
        return self.filter(location_type__in=location_types)

    def overlapping(self, date_from, date_to):
        """The events sharing at least a day with the range; either end may be left open."""
        if date_from and date_to and date_to < date_from:
            return self.none()
        overlapping = self
        if date_from:
            overlapping = overlapping.filter(end_date__gte=date_from)
        if date_to:
            overlapping = overlapping.filter(start_date__lte=date_to)
        return overlapping

    def free(self):
        return self.filter(price=0)

    def most_relevant_first(self):
        """After `search()`: ties go to the nearest."""
        return self.order_by("-relevance", "start_date", "start_time")

    def _within(self, subcategories):
        """`OTHER` also brings back the free text typed when no subcategory fits."""
        match = models.Q(subcategory__in=subcategories)
        if Event.Subcategory.OTHER in subcategories:
            match |= ~models.Q(subcategory__in=Event.Subcategory.values)
        return self.filter(match)


class Event(SlugFromTitleMixin, BaseModel):
    SLUG_FALLBACK = "evenement"

    class Category(models.TextChoices):
        INFORMATION = "information", _("Information")
        EMPLOYMENT = "employment", _("Emploi")
        GUIDANCE = "guidance", _("Orientation")
        SOCIAL = "social", _("Convivial")

    class Subcategory(models.TextChoices):
        CONFERENCE = "conference", _("Conférence")
        WORKSHOP = "workshop", _("Atelier")
        WEBINAR = "webinar", _("Webinaire d'info")
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

        @classmethod
        def sorted_choices(cls):
            """The order a select offers them in: alphabetical, accents ignored, with "Autre"
            last — it is the prompt for what the list does not hold, not a type among them."""
            listed = [choice for choice in cls.choices if choice[0] != cls.OTHER]
            listed.sort(key=lambda choice: strip_accents(str(choice[1])).lower())
            return [*listed, (cls.OTHER.value, cls.OTHER.label)]

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
            Subcategory.HACKATHON,
        ),
    }

    CATEGORY_COLORS = {
        Category.INFORMATION: "orange",
        Category.EMPLOYMENT: "yellow",
        Category.GUIDANCE: "green",
        Category.SOCIAL: "purple",
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
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_("slug"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    # A `Subcategory` value, or the free text typed when none of them fits.
    subcategory = models.CharField(max_length=22, verbose_name=_("sous-catégorie"))
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
    # Derived on save from `cog_code`, or `postal_code` without one.
    department_code = models.CharField(
        max_length=3, blank=True, db_index=True, verbose_name=_("code du département")
    )
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
    image = models.FileField(
        max_length=255, blank=True, storage=public_storage, verbose_name=_("visuel")
    )  # Uploaded by the browser straight to the bucket: the column only ever receives its key.
    image_alt = models.CharField(
        max_length=255, blank=True, verbose_name=_("alternative textuelle du visuel")
    )
    image_credit = models.CharField(max_length=255, blank=True, verbose_name=_("crédit du visuel"))
    search_vector = models.GeneratedField(
        expression=search_vector(("title", "A"), ("organizer", "B"), ("description", "C")),
        output_field=SearchVectorField(),
        db_persist=True,
    )

    objects = EventQuerySet.as_manager()
    history = HistoricalRecords(excluded_fields=["search_vector"])

    class Meta:
        verbose_name = _("événement")
        verbose_name_plural = _("événements")
        ordering = ["start_date", "start_time"]
        indexes = [GinIndex(fields=["search_vector"], name="event_search_vector")]
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

    def save(self, *args, **kwargs):
        self.department_code = department_code(self.cog_code, self.postal_code)
        super().save(*args, **kwargs)

    def is_organized_by(self, user):
        return self.created_by_id == user.pk

    def fill_from(self, forms):
        """The funnel screens, written onto the columns they collect between them: each says
        for itself which ones those are."""
        for form in forms:
            for field, value in form.event_fields.items():
                setattr(self, field, value)

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
        return next(
            category
            for category, subcategories in self.SUBCATEGORIES.items()
            if self._listed_subcategory in subcategories
        )

    @property
    def category_label(self):
        return self.Category(self.category).label

    @property
    def category_color(self):
        return self.CATEGORY_COLORS[self.category]

    @property
    def image_url(self):
        """Without a visual of its own, the event displays the default one of its subcategory."""
        if self.image:
            return self.image.url
        return static(f"images/events/{self.category}/{self._listed_subcategory}.webp")

    @property
    def date_range_label(self):
        """ "du 12 au 14 juin 2026": what both dates share is only written once."""
        if self.start_date == self.end_date:
            return f"le {date_format(self.end_date, 'j F Y')}"
        return (
            f"du {date_format(self.start_date, self._range_start_format)} "
            f"au {date_format(self.end_date, 'j F Y')}"
        )

    @property
    def is_approved(self):
        return self.status == Event.Status.APPROVED

    @property
    def has_ended(self):
        end = timezone.make_aware(datetime.combine(self.end_date, self.end_time))
        return end < timezone.now()

    @property
    def price_label(self):
        """A no-break space, not an entity: this is text, templates would escape `&nbsp;`."""
        return "gratuit" if not self.price else f"{floatformat(self.price, '-2')} €"

    @property
    def _listed_subcategory(self):
        """Free text is an unlisted subcategory, so it belongs where `OTHER` does."""
        if self.subcategory in self.Subcategory.values:
            return self.subcategory
        return self.Subcategory.OTHER

    @property
    def _range_start_format(self):
        if self.start_date.year != self.end_date.year:
            return "j F Y"
        return "j" if self.start_date.month == self.end_date.month else "j F"
