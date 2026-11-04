from datetime import UTC, datetime

import pytest
from django.core.exceptions import ValidationError

from techpourtoutes.models import JobPosting

from ..views.test_beneficiary_views import save_job_posting

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
