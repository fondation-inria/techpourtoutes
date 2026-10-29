from datetime import UTC, datetime

import pytest

from techpourtoutes.models import JobPosting

pytestmark = pytest.mark.django_db


def _job_posting(external_id, **overrides):
    job_posting = JobPosting(
        source=JobPosting.Source.MYFUTURE,
        external_id=external_id,
        title="Développeuse web",
        company_name="Octo",
        description="Une alternance en développement.",
        city="Paris",
        domains=["informatique"],
        category=JobPosting.Category.APPRENTICESHIP,
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        url="https://www.myfuture.fr/offre/1",
        **overrides,
    )
    job_posting.save()
    return job_posting


def test_objects_leaves_out_the_hidden_offers():
    _job_posting("shown")
    _job_posting("hidden", hidden=True)

    assert list(JobPosting.objects.values_list("external_id", flat=True)) == ["shown"]


def test_all_objects_lists_the_hidden_offers_too():
    _job_posting("shown")
    _job_posting("hidden", hidden=True)

    assert set(JobPosting.all_objects.values_list("external_id", flat=True)) == {
        "shown",
        "hidden",
    }
