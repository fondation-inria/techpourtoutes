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


class Event(BaseModel):
    class Category(models.TextChoices):
        SALON = "salon", _("Salon")
        JOB_FAIR = "job_fair", _("Forum de l'emploi")
        SPEED_DATING = "speed_dating", _("Speed dating")
        JOB_DATING = "job_dating", _("Job dating")
        AFTERWORK = "afterwork", _("Afterwork")
        CONFERENCE = "conference", _("Conférence")
        WORKSHOP = "workshop", _("Atelier")
        WEBINAR = "webinar", _("Webinaire d'informations")
        OPEN_HOUSE = "open_house", _("Portes ouvertes")
        LEARNING_EXPEDITION = "learning_expedition", _("Learning expédition")
        JOB_SHADOWING = "job_shadowing", _("Vis-ma-vie")
        VISIT = "visit", _("Visite")
        HACKATHON = "hackathon", _("Hackathon")
        CEREMONY = "ceremony", _("Cérémonie")
        ROUND_TABLE = "round_table", _("Table ronde")
        OTHER = "other", _("Autre")

    class LocationType(models.TextChoices):
        PHYSICAL = "physical", _("En présentiel")
        ONLINE = "online", _("En ligne")

    class ReservationType(models.TextChoices):
        CANDIDACY = "candidacy", _("Candidature")
        RESERVATION = "reservation", _("Réservation")
        OPEN = "open", _("Accès libre")

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
    # A `Category` value, or the free text typed when none of them fits.
    category = models.CharField(max_length=100, verbose_name=_("catégorie"))
    start_date = models.DateField(verbose_name=_("date de début"))
    end_date = models.DateField(verbose_name=_("date de fin"))
    start_time = models.TimeField(verbose_name=_("heure de début"))
    end_time = models.TimeField(verbose_name=_("heure de fin"))
    location_type = models.CharField(
        max_length=10, choices=LocationType.choices, verbose_name=_("format")
    )
    address = models.CharField(max_length=255, blank=True, verbose_name=_("adresse"))
    postal_code = models.CharField(max_length=10, blank=True, verbose_name=_("code postal"))
    city = models.CharField(max_length=100, blank=True, verbose_name=_("commune"))
    cog_code = models.CharField(max_length=10, blank=True, verbose_name=_("COG de la commune"))
    longitude = models.FloatField(null=True, blank=True, verbose_name=_("longitude"))
    latitude = models.FloatField(null=True, blank=True, verbose_name=_("latitude"))
    ban_id = models.CharField(max_length=30, blank=True, verbose_name=_("identifiant BAN"))
    online_url = models.URLField(blank=True, verbose_name=_("lien de connexion"))
    event_url = models.URLField(blank=True, verbose_name=_("lien vers l'événement"))
    reservation_type = models.CharField(
        max_length=20, choices=ReservationType.choices, verbose_name=_("modalité d'inscription")
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
        ]

    def __str__(self):
        return self.title

    @property
    def category_label(self):
        """The free text stands in for the label when the category is not a listed one."""
        if self.category in self.Category.values:
            return self.Category(self.category).label
        return self.category
