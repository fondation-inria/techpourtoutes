from datetime import date, datetime, timedelta

from django.utils import timezone

from techpourtoutes.templatetags.date_filters import iso_date, time_ago


def test_iso_date_formats_date_objects():
    assert iso_date(date(2008, 3, 15)) == "2008-03-15"
    assert iso_date(datetime(2008, 3, 15, 14, 30)) == "2008-03-15"


def test_iso_date_passes_strings_through():
    assert iso_date("2008-03-15") == "2008-03-15"


def test_iso_date_empty_values():
    assert iso_date(None) == ""
    assert iso_date("") == ""


def test_time_ago_keeps_only_the_largest_unit():
    assert time_ago(timezone.now() - timedelta(days=17, hours=5)) == "il y a 2\xa0semaines"
    assert time_ago(timezone.now() - timedelta(days=3, hours=5)) == "il y a 3\xa0jours"
