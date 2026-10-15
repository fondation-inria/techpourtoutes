from datetime import timedelta

from techpourtoutes.tests.birth_dates import birth_date_for_age
from techpourtoutes.utils.dates import compute_age


def test_compute_age_counts_the_birthday_reached_today():
    assert compute_age(birth_date_for_age(18)) == 18


def test_compute_age_waits_for_the_birthday():
    assert compute_age(birth_date_for_age(18) + timedelta(days=1)) == 17
