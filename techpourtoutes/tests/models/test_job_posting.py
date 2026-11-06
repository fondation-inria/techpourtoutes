from datetime import UTC, datetime, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from techpourtoutes.models import JobPosting

from ..views.test_beneficiary_views import save_job_posting

pytestmark = pytest.mark.django_db


def _job_posting(external_id, **overrides):
    job_posting = JobPosting(
        **{
            "source": JobPosting.Source.MYFUTURE,
            "external_id": external_id,
            "title": "Développeuse web",
            "company_name": "Octo",
            "description": "Une alternance en développement.",
            "city": "Paris",
            "domains": ["informatique"],
            "category": JobPosting.Category.APPRENTICESHIP,
            "published_at": datetime(2026, 1, 1, tzinfo=UTC),
            "url": "https://www.myfuture.fr/offre/1",
            **overrides,
        }
    )
    job_posting.save()
    return job_posting


def test_objects_leaves_out_the_hidden_offers():
    _job_posting("shown")
    _job_posting("hidden", hidden=True)

    assert list(JobPosting.objects.values_list("external_id", flat=True)) == ["shown"]


def test_objects_leaves_out_the_hidden_offers_whatever_the_filters():
    _job_posting("shown", department_code="29")
    _job_posting("hidden", department_code="29", hidden=True)

    postings = JobPosting.objects.in_departments(["29"])

    assert list(postings.values_list("external_id", flat=True)) == ["shown"]


def test_all_objects_lists_the_hidden_offers_too():
    _job_posting("shown")
    _job_posting("hidden", hidden=True)

    assert set(JobPosting.all_objects.values_list("external_id", flat=True)) == {
        "shown",
        "hidden",
    }


def test_job_posting_rejects_a_domain_outside_the_choices():
    with pytest.raises(ValidationError, match="domains"):
        save_job_posting(
            "Stage", JobPosting.Category.HIGHER_ED_INTERNSHIP, domains=["Développement web"]
        )


def test_job_posting_domains_are_the_normalized_list():
    assert JobPosting.Domain.labels == [
        "Électronique",
        "Électrotechnique",
        "Télécommunications",
        "Bases de données",
        "Développement - programmation - logiciel",
        "Informatique de gestion",
        "Informatique",
        "Informatique industrielle",
        "Informatique pour la recherche",
        "Systèmes et réseaux",
        "Mathématiques",
        "Sciences de l’univers",
        "Exploitation, maintenance informatique",
        "Maîtrise d’ouvrage et fonctionnel",
        "Création",
        "Conception, recherche",
        "Direction recherche et développement",
        "Projets scientifiques et techniques",
        "Test, essai, validation, expertise",
    ]


# 23:30 in Paris: an hour later is the next day there, though not in UTC.
CREATED_AT = datetime(2026, 1, 1, 22, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("source_updated_at", "updated_at", "last_updated_at"),
    [
        (datetime(2026, 2, 1, tzinfo=UTC), CREATED_AT, datetime(2026, 2, 1, tzinfo=UTC)),
        (None, CREATED_AT + timedelta(hours=1), CREATED_AT + timedelta(hours=1)),
        (None, CREATED_AT + timedelta(minutes=20), None),
    ],
    ids=["the partner's date first", "ours on a later day", "none the day of its creation"],
)
def test_with_last_updated_at(source_updated_at, updated_at, last_updated_at):
    _job_posting("posting", source_updated_at=source_updated_at)
    # Written along: the trigger leaves `updated_at` alone.
    JobPosting.objects.update(created_at=CREATED_AT, updated_at=updated_at)

    assert JobPosting.objects.with_last_updated_at().get().last_updated_at == last_updated_at


def test_latest_first_sorts_by_the_date_last_updated_at_shows():
    now = timezone.now()
    _job_posting("published yesterday", published_at=now - timedelta(days=1))
    _job_posting(
        "updated by the partner two days ago",
        published_at=now - timedelta(days=30),
        source_updated_at=now - timedelta(days=2),
    )
    _job_posting("updated by us today", published_at=now - timedelta(days=30))
    _job_posting("updated the day of its creation", published_at=now - timedelta(days=20))
    JobPosting.objects.filter(external_id="updated by us today").update(
        created_at=now - timedelta(days=30)
    )
    JobPosting.objects.filter(external_id="updated the day of its creation").update(
        created_at=now - timedelta(days=10), updated_at=now - timedelta(days=10)
    )

    assert list(JobPosting.objects.latest_first().values_list("external_id", flat=True)) == [
        "updated by us today",
        "published yesterday",
        "updated by the partner two days ago",
        "updated the day of its creation",
    ]


@pytest.mark.parametrize(
    ("street", "postal_code", "city", "label"),
    [
        ("12 rue de la Mer", "13000", "Marseille", "12 rue de la Mer, 13000 Marseille"),
        ("10 rue Palissy 53960 Bonchamp", "53960", "Bonchamp", "10 rue Palissy 53960 Bonchamp"),
        (
            "27 place Jules Guesde 13481 Marseille cedex 20",
            "13001",
            "Marseille 01",
            "27 place Jules Guesde 13481 Marseille cedex 20",
        ),
        ("", "13000", "Marseille", "13000 Marseille"),
        ("", "", "Paris 01", "Paris 01"),
    ],
)
def test_address_label_does_not_repeat_what_the_street_already_says(
    street, postal_code, city, label
):
    job_posting = JobPosting(street=street, postal_code=postal_code, city=city)

    assert job_posting.address_label == label


@pytest.mark.parametrize(
    ("durations", "kept"),
    [
        (["under_3_months"], {"none", "2"}),
        (["3_to_6_months"], {"none", "3", "6"}),
        (["7_to_12_months"], {"none", "7", "12"}),
        (["over_12_months"], {"none", "13"}),
        (["under_3_months", "over_12_months"], {"none", "2", "13"}),
        ([], {"none", "2", "3", "6", "7", "12", "13"}),
    ],
)
def test_with_durations_keeps_the_ticked_ranges_and_the_postings_without_a_duration(
    durations, kept
):
    for months in (None, 2, 3, 6, 7, 12, 13):
        _job_posting(str(months).lower(), duration_months=months)

    postings = JobPosting.objects.with_durations(durations)

    assert set(postings.values_list("external_id", flat=True)) == kept
