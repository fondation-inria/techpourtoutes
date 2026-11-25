from datetime import datetime

import pytest
from django.utils import timezone

from techpourtoutes.utils.time_zones import (
    TimeZone,
    time_zone_for,
    wall_clock_furthest_behind,
)


@pytest.mark.parametrize(
    ("postal_code", "time_zone"),
    [
        ("97110", TimeZone.GUADELOUPE),
        ("97133", TimeZone.GUADELOUPE),  # Saint-Barthélemy
        ("97150", TimeZone.GUADELOUPE),  # Saint-Martin
        ("97200", TimeZone.MARTINIQUE),
        ("97300", TimeZone.GUYANE),
        ("97400", TimeZone.REUNION),
        ("97500", TimeZone.SAINT_PIERRE_ET_MIQUELON),
        ("97600", TimeZone.MAYOTTE),
        ("98600", TimeZone.WALLIS_ET_FUTUNA),
        ("98714", TimeZone.TAHITI),
        ("98800", TimeZone.NOUVELLE_CALEDONIE),
    ],
)
def test_time_zone_for_reads_an_overseas_postal_code(postal_code, time_zone):
    assert time_zone_for(postal_code) == time_zone


@pytest.mark.parametrize("postal_code", ["75001", "20000", "98000", ""])
def test_time_zone_for_falls_back_to_paris(postal_code):
    """Monaco's 98000 included: it is not one of the overseas prefixes."""
    assert time_zone_for(postal_code) == TimeZone.PARIS


def test_wall_clock_furthest_behind_reads_the_clock_of_tahiti(monkeypatch):
    """At 15:00 in Paris on October 1st (UTC+2), it is still 03:00 in Tahiti (UTC-10)."""
    now = timezone.make_aware(datetime(2026, 10, 1, 15, 0))
    monkeypatch.setattr(timezone, "now", lambda: now)

    assert wall_clock_furthest_behind() == datetime(2026, 10, 1, 3, 0)
