from datetime import UTC, datetime

import pytest
from django.urls import reverse

from techpourtoutes.models import JobPosting

CHANGELIST = "admin:techpourtoutes_jobposting_changelist"
Category = JobPosting.Category


def _job_posting(**overrides):
    job_posting = JobPosting(
        **{
            "source": JobPosting.Source.MYFUTURE,
            "external_id": "mf-1",
            "title": "Développeuse web",
            "company_name": "Octo",
            "description": "Une alternance en développement.",
            "postal_code": "75011",
            "cog_code": "75111",
            "city": "Paris",
            "domains": ["informatique"],
            "duration": "12 mois",
            "category": Category.APPRENTICESHIP,
            "contract_type": JobPosting.ContractType.APPRENTICESHIP,
            "published_at": datetime(2026, 1, 1, tzinfo=UTC),
            "url": "https://www.myfuture.fr/offre/1",
            **overrides,
        }
    )
    job_posting.save()
    return job_posting


@pytest.fixture
def job_postings(db):
    return {
        "apprenticeship": _job_posting(),
        "troisieme": _job_posting(
            source=JobPosting.Source.APEC,
            external_id="apec-1",
            title="Stage d'observation",
            company_name="Mairie de Lyon",
            category=Category.TROISIEME_INTERNSHIP,
            contract_type="",
        ),
        "cdi": _job_posting(
            external_id="mf-2",
            title="Data analyste",
            company_name="Doctolib",
            category=Category.FIRST_JOB,
            contract_type=JobPosting.ContractType.CDI,
        ),
    }


def _listed_titles(client, **params):
    response = client.get(reverse(CHANGELIST), params)
    return {job_posting.title for job_posting in response.context["cl"].result_list}


@pytest.mark.django_db
def test_job_posting_changelist_shows_title_company_source_and_type(
    verified_admin_client, job_postings
):
    content = verified_admin_client.get(reverse(CHANGELIST)).content.decode()
    assert "Stage d&#x27;observation" in content
    assert "Mairie de Lyon" in content
    assert "Apec" in content
    assert "Stage de troisième" in content
    assert "Contrat d&#x27;apprentissage" in content


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("query", "expected"),
    [("analyste", {"Data analyste"}), ("doctolib", {"Data analyste"})],
)
def test_job_posting_changelist_searches_title_and_company(
    verified_admin_client, job_postings, query, expected
):
    assert _listed_titles(verified_admin_client, q=query) == expected


@pytest.mark.django_db
def test_job_posting_changelist_filters_by_source(verified_admin_client, job_postings):
    assert _listed_titles(verified_admin_client, source__exact="apec") == {"Stage d'observation"}


@pytest.mark.django_db
def test_job_posting_changelist_filters_by_category(verified_admin_client, job_postings):
    titles = _listed_titles(verified_admin_client, category__exact=Category.TROISIEME_INTERNSHIP)
    assert titles == {"Stage d'observation"}


@pytest.mark.django_db
def test_job_posting_changelist_filters_by_contract_type(verified_admin_client, job_postings):
    assert _listed_titles(verified_admin_client, contract_type__exact="cdi") == {"Data analyste"}


@pytest.mark.django_db
def test_job_posting_page_shows_every_field_read_only(verified_admin_client, job_postings):
    job_posting = job_postings["apprenticeship"]
    url = reverse("admin:techpourtoutes_jobposting_change", args=[job_posting.pk])
    response = verified_admin_client.get(url)
    content = response.content.decode()

    for value in (
        "mf-1",
        "Une alternance en développement.",
        "75011",
        "75111",
        "informatique",
        "12 mois",
        "Alternance",
        "https://www.myfuture.fr/offre/1",
        "Créé le",
    ):
        assert value in content
    assert 'name="title"' not in content
