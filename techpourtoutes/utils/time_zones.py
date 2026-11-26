from zoneinfo import ZoneInfo

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeZone(models.TextChoices):
    """The time zones of France, overseas included. Tahiti is used for all French Polynesia."""

    PARIS = "Europe/Paris", _("heure de Paris")
    GUADELOUPE = "America/Guadeloupe", _("heure de la Guadeloupe")
    GUYANE = "America/Cayenne", _("heure de la Guyane")
    REUNION = "Indian/Reunion", _("heure de La Réunion")
    MARTINIQUE = "America/Martinique", _("heure de la Martinique")
    MAYOTTE = "Indian/Mayotte", _("heure de Mayotte")
    NOUVELLE_CALEDONIE = "Pacific/Noumea", _("heure de la Nouvelle-Calédonie")
    SAINT_PIERRE_ET_MIQUELON = "America/Miquelon", _("heure de Saint-Pierre-et-Miquelon")
    TAHITI = "Pacific/Tahiti", _("heure de Tahiti")
    WALLIS_ET_FUTUNA = "Pacific/Wallis", _("heure de Wallis-et-Futuna")


# Saint-Barthélemy and Saint-Martin have postal codes of Guadeloupe, on the same clock.
_BY_POSTAL_CODE_PREFIX = {
    "971": TimeZone.GUADELOUPE,
    "972": TimeZone.MARTINIQUE,
    "973": TimeZone.GUYANE,
    "974": TimeZone.REUNION,
    "975": TimeZone.SAINT_PIERRE_ET_MIQUELON,
    "976": TimeZone.MAYOTTE,
    "986": TimeZone.WALLIS_ET_FUTUNA,
    "987": TimeZone.TAHITI,
    "988": TimeZone.NOUVELLE_CALEDONIE,
}


def time_zone_for(postal_code):
    return _BY_POSTAL_CODE_PREFIX.get(postal_code[:3], TimeZone.PARIS)


def wall_clock_in(time_zone):
    return timezone.localtime(timezone=ZoneInfo(time_zone)).replace(tzinfo=None)


def wall_clock_furthest_behind():
    """What the clock reads where it reads earliest: whatever is over there is over everywhere."""
    return min(wall_clock_in(time_zone) for time_zone in TimeZone.values)
