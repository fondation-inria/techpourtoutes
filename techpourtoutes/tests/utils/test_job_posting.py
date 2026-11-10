from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from techpourtoutes.models import JobPosting
from techpourtoutes.utils.job_posting import city_name, upsert_in_batches

pytestmark = pytest.mark.django_db


def _posting(external_id, title="Développeuse"):
    return JobPosting(
        source=JobPosting.Source.APEC,
        external_id=external_id,
        title=title,
        company_name="Apec",
        description="…",
        city="Paris",
        domains=[JobPosting.Domain.DEVELOPPEMENT],
        category=JobPosting.Category.FIRST_JOB,
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        url=f"https://www.apec.fr/offre/{external_id}",
    )


def test_the_postings_are_written_one_batch_at_a_time(django_assert_num_queries):
    """Only one batch is held in memory, whatever the number of offers."""
    with patch("techpourtoutes.utils.job_posting.BATCH_SIZE", 2), django_assert_num_queries(2):
        upsert_in_batches((_posting(letter) for letter in "abc"), update_fields=["title"])

    assert JobPosting.objects.count() == 3


def test_a_posting_already_written_is_updated_in_place():
    upsert_in_batches([_posting("a")], update_fields=["title"])

    upsert_in_batches([_posting("a", title="Data Engineer")], update_fields=["title"])

    assert JobPosting.objects.get().title == "Data Engineer"


def test_the_ids_written_are_handed_back():
    """What the source still lists: the caller deletes the rest."""
    assert upsert_in_batches([_posting("a"), _posting("b")], update_fields=["title"]) == ["a", "b"]


@pytest.mark.parametrize(
    ("city", "name"),
    [
        ("ST GRATIEN", "St Gratien"),
        ("PARIS 01", "Paris 01"),
        ("Aire-sur-l'Adour", "Aire-sur-l'Adour"),
        ("Pont-l'Abbé", "Pont-l'Abbé"),
    ],
)
def test_city_name_title_cases_only_a_city_spelled_in_capitals(city, name):
    assert city_name(city) == name
