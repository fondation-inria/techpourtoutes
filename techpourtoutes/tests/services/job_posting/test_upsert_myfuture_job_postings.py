from datetime import UTC, datetime

import pytest

from techpourtoutes.models import JobPosting
from techpourtoutes.services.job_posting.upsert_myfuture_job_postings import (
    UpsertMyFutureJobPostings,
)

pytestmark = pytest.mark.django_db

Category = JobPosting.Category


def test_an_offer_is_mapped_onto_a_job_posting(myfuture_record):
    result = UpsertMyFutureJobPostings(records=[myfuture_record()])

    assert result.success
    posting = JobPosting.objects.get()
    assert posting.source == JobPosting.Source.MYFUTURE
    assert posting.external_id == "22NisRqehckrMvEu3"
    assert posting.title == "Stage en électricité générale"
    assert posting.company_name == "Didier Ducom"
    assert posting.description == "<p>Explorez le métier d’électricien.</p>"
    assert posting.postal_code == "32110"
    assert posting.cog_code == "32094"
    assert posting.city == "Caupenne-d'Armagnac"
    assert posting.domains == ["électrotechnique"]
    assert posting.duration == ""
    assert posting.company_logo == ""
    assert posting.categories == [Category.TROISIEME_INTERNSHIP]
    assert posting.contract_type == ""
    assert posting.published_at == datetime(2025, 1, 6, 8, 21, 32, 994000, tzinfo=UTC)
    assert posting.source_updated_at == datetime(2025, 3, 11, 13, 56, 31, 694000, tzinfo=UTC)
    assert posting.url == "https://myfutu.re/internships/offers/22NisRqehckrMvEu3"


def test_the_optional_address_fields_and_the_logo_are_read_when_present(myfuture_record):
    record = myfuture_record(
        address={"street": "1 rue", "departmentCode": "92", "city": "Puteaux"},
        owner_logo="https://myfuture.s3.fr-par.scw.cloud/prod/logos/abc/logo-0",
    )

    UpsertMyFutureJobPostings(records=[record])

    posting = JobPosting.objects.get()
    assert posting.postal_code == ""
    assert posting.cog_code == ""
    assert posting.company_logo == "https://myfuture.s3.fr-par.scw.cloud/prod/logos/abc/logo-0"


@pytest.mark.parametrize(
    ("internship_type", "category"),
    [
        ("3eInternship", Category.TROISIEME_INTERNSHIP),
        ("highSchoolInternship", Category.SECONDE_INTERNSHIP),
        ("studentInternship", Category.HIGHER_ED_INTERNSHIP),
        ("apprenticeship", Category.APPRENTICESHIP),
        ("pmsmp", Category.FIRST_JOB),
    ],
)
def test_each_internship_type_lands_in_its_category(myfuture_record, internship_type, category):
    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=[internship_type])])

    assert JobPosting.objects.get().categories == [category]


def test_the_internship_types_are_read_whatever_their_case(myfuture_record):
    """MyFuture sends `PMSMP` and `3einternship` alongside their usual spelling."""
    record = myfuture_record(internshipTypes=["PMSMP", "3einternship"])

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().categories == [
        Category.FIRST_JOB,
        Category.TROISIEME_INTERNSHIP,
    ]


def test_an_offer_open_to_several_audiences_keeps_every_category(myfuture_record):
    record = myfuture_record(internshipTypes=["highSchoolInternship", "studentInternship"])

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().categories == [
        Category.SECONDE_INTERNSHIP,
        Category.HIGHER_ED_INTERNSHIP,
    ]


def test_the_types_without_a_category_are_left_out(myfuture_record):
    record = myfuture_record(internshipTypes=["3eInternship", "miniInternship", "visit"])

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().categories == [Category.TROISIEME_INTERNSHIP]


@pytest.mark.parametrize("internship_types", [[], ["miniInternship"], ["visit"]])
def test_an_offer_without_any_category_is_not_imported(myfuture_record, internship_types):
    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=internship_types)])

    assert not JobPosting.objects.exists()


def test_an_apprenticeship_is_an_apprenticeship_contract(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=["apprenticeship"])])

    assert JobPosting.objects.get().contract_type == JobPosting.ContractType.APPRENTICESHIP


def test_an_offer_without_a_city_is_not_imported(myfuture_record):
    record = myfuture_record(address={"street": "Place du général de Gaulle", "postalCode": ""})

    UpsertMyFutureJobPostings(records=[record])

    assert not JobPosting.objects.exists()


def test_only_the_sub_domains_we_follow_become_domains(myfuture_record):
    record = myfuture_record(
        subDomainKeys=[
            "commerce-marketing-ventemarketing-vente",
            "informatique-internetsystemes-et-reseaux",
            "sciencesmathematiques",
        ]
    )

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().domains == ["systèmes et réseaux", "mathématiques"]


def test_the_description_keeps_its_layout_but_loses_whatever_could_run(myfuture_record):
    record = myfuture_record(
        description=(
            '<h2 id="x" style="color: red">Missions</h2>'
            "<ul><li><strong>Coder</strong></li></ul>"
            '<p onclick="steal()">Voir <a href="https://example.org" target="_blank">ici</a></p>'
            '<iframe src="https://example.org"></iframe><script>steal()</script>'
        )
    )

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().description == (
        "<h2>Missions</h2>"
        "<ul><li><strong>Coder</strong></li></ul>"
        '<p>Voir <a href="https://example.org" rel="noopener noreferrer">ici</a></p>'
    )


def test_an_offer_already_imported_is_updated_in_place(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record()])
    first_pk = JobPosting.objects.get().pk

    UpsertMyFutureJobPostings(records=[myfuture_record(title="Stage en domotique")])

    posting = JobPosting.objects.get()
    assert posting.pk == first_pk
    assert posting.title == "Stage en domotique"


def test_an_offer_myfuture_no_longer_lists_is_deleted(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record("kept"), myfuture_record("gone")])

    UpsertMyFutureJobPostings(records=[myfuture_record("kept")])

    assert list(JobPosting.objects.values_list("external_id", flat=True)) == ["kept"]


def test_an_offer_that_lost_its_last_category_is_deleted(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record()])

    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=["visit"])])

    assert not JobPosting.objects.exists()


def test_the_other_sources_offers_are_left_alone(myfuture_record):
    JobPosting(
        source=JobPosting.Source.APEC,
        external_id="apec-1",
        title="Développeuse",
        company_name="Apec",
        description="…",
        city="Paris",
        domains=["informatique"],
        categories=[Category.FIRST_JOB],
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        url="https://www.apec.fr/offre/1",
    ).save()

    UpsertMyFutureJobPostings(records=[myfuture_record()])

    assert JobPosting.objects.filter(source=JobPosting.Source.APEC).exists()
