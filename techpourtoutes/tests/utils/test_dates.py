from datetime import timedelta

from techpourtoutes.utils.dates import adult_birth_date, compute_age


def test_adult_birth_date_turns_eighteen_today():
    assert compute_age(adult_birth_date()) == 18


def test_a_birth_date_past_the_cutoff_is_still_a_minor():
    assert compute_age(adult_birth_date() + timedelta(days=1)) == 17
