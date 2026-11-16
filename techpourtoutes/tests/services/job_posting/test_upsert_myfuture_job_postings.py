from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from techpourtoutes.models import JobPosting
from techpourtoutes.services.job_posting.upsert_myfuture_job_postings import (
    UpsertMyFutureJobPostings,
)

pytestmark = pytest.mark.django_db

Category = JobPosting.Category

LAST_WEEK = datetime(2026, 10, 27, tzinfo=UTC)


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
    assert posting.department_code == "32"
    assert posting.city == "Caupenne-d'Armagnac"
    assert posting.domains == [JobPosting.Domain.ELECTROTECHNIQUE]
    assert posting.duration_months is None
    assert posting.company_logo == ""
    assert posting.category == Category.TROISIEME_INTERNSHIP
    assert posting.contract_type == ""
    assert posting.published_at == datetime(2025, 1, 6, 8, 21, 32, 994000, tzinfo=UTC)
    assert posting.source_updated_at == datetime(2025, 3, 11, 13, 56, 31, 694000, tzinfo=UTC)
    assert posting.url == "https://myfutu.re/internships/offers/22NisRqehckrMvEu3"


@pytest.mark.parametrize(
    ("city", "name"),
    [("BONCHAMP LES LAVAL", "Bonchamp Les Laval"), ("Aire-sur-l'Adour", "Aire-sur-l'Adour")],
)
def test_a_city_spelled_in_capitals_is_title_cased(myfuture_record, city, name):
    record = myfuture_record(address={"postalCode": "53960", "city": city})

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().city == name


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
        ("studentInternship", Category.HIGHER_ED_INTERNSHIP),
        ("highSchoolInternship", Category.PFMP),
        ("apprenticeship", Category.APPRENTICESHIP),
        ("pmsmp", Category.FIRST_JOB),
    ],
)
def test_each_internship_type_lands_in_its_category(myfuture_record, internship_type, category):
    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=[internship_type])])

    assert JobPosting.objects.get().category == category


@pytest.mark.parametrize(
    ("internship_type", "category"),
    [
        ("PMSMP", Category.FIRST_JOB),
        ("3einternship", Category.TROISIEME_INTERNSHIP),
        ("3eInternShip", Category.TROISIEME_INTERNSHIP),
    ],
)
def test_the_internship_types_are_read_whatever_their_case(
    myfuture_record, internship_type, category
):
    """MyFuture sends these alongside their usual spelling."""
    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=[internship_type])])

    assert JobPosting.objects.get().category == category


@pytest.mark.parametrize(
    "internship_types", [["pmsmp", "3eInternship"], ["3eInternship", "pmsmp"]]
)
def test_an_offer_of_several_types_lands_in_a_single_category(myfuture_record, internship_types):
    """A handful of offers are tagged both 3e and PMSMP, in either order."""
    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=internship_types)])

    assert JobPosting.objects.get().category == Category.TROISIEME_INTERNSHIP


def test_a_pfmp_also_open_to_students_is_a_higher_ed_internship(myfuture_record):
    """Nearly half the PFMPs are also tagged studentInternship, mostly offers made for
    students: the PFMP tab keeps to those meant for lycée pro pupils alone."""
    record = myfuture_record(internshipTypes=["highSchoolInternship", "studentInternship"])

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().category == Category.HIGHER_ED_INTERNSHIP


def test_the_types_without_a_category_are_left_out(myfuture_record):
    record = myfuture_record(internshipTypes=["3eInternship", "miniInternship", "visit"])

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().category == Category.TROISIEME_INTERNSHIP


@pytest.mark.parametrize("internship_types", [[], ["miniInternship"], ["visit"]])
def test_an_offer_without_any_category_is_not_imported(myfuture_record, internship_types):
    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=internship_types)])

    assert not JobPosting.objects.exists()


def test_an_apprenticeship_is_an_apprenticeship_contract(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=["apprenticeship"])])

    assert JobPosting.objects.get().contract_type == JobPosting.ContractType.APPRENTICESHIP


def test_a_pmsmp_is_an_immersion_contract(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=["pmsmp"])])

    assert JobPosting.objects.get().contract_type == JobPosting.ContractType.PMSMP


def test_an_offer_without_a_city_is_not_imported(myfuture_record):
    record = myfuture_record(address={"street": "Place du général de Gaulle", "postalCode": ""})

    UpsertMyFutureJobPostings(records=[record])

    assert not JobPosting.objects.exists()


def test_an_offer_whose_periods_have_all_passed_is_not_imported(myfuture_record):
    record = myfuture_record(periods=[_period(days_from_now=-30), _period(days_from_now=-10)])

    UpsertMyFutureJobPostings(records=[record])

    assert not JobPosting.objects.exists()


def test_an_offer_with_a_period_still_to_come_is_imported(myfuture_record):
    record = myfuture_record(periods=[_period(days_from_now=-30), _period(days_from_now=10)])

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.exists()


def test_an_offer_whose_last_period_has_passed_is_deleted(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record(periods=[_period(days_from_now=10)])])

    UpsertMyFutureJobPostings(records=[myfuture_record(periods=[_period(days_from_now=-10)])])

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

    assert JobPosting.objects.get().domains == [
        JobPosting.Domain.SYSTEMES_ET_RESEAUX,
        JobPosting.Domain.MATHEMATIQUES,
    ]


def test_the_description_shows_the_line_breaks_typed_in_the_text(myfuture_record):
    record = myfuture_record(description="<p>Description de l’atelier\nNotre atelier</p>")

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().description == (
        "<p>Description de l’atelier<br>Notre atelier</p>"
    )


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


def test_an_offer_myfuture_lists_unchanged_keeps_its_update_date(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record()])
    JobPosting.objects.update(updated_at=LAST_WEEK)

    UpsertMyFutureJobPostings(records=[myfuture_record()])

    assert JobPosting.objects.get().updated_at == LAST_WEEK


def test_an_offer_that_changed_moves_its_update_date(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record()])
    JobPosting.objects.update(updated_at=LAST_WEEK)

    UpsertMyFutureJobPostings(records=[myfuture_record(title="Stage en domotique")])

    assert JobPosting.objects.get().updated_at > timezone.now() - timedelta(minutes=1)


def test_an_offer_unpublished_by_hand_stays_unpublished_once_updated(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record()])
    JobPosting.objects.update(hidden=True)

    UpsertMyFutureJobPostings(records=[myfuture_record(title="Stage en domotique")])

    posting = JobPosting.all_objects.get()
    assert posting.title == "Stage en domotique"
    assert posting.hidden


def test_an_offer_myfuture_no_longer_lists_is_deleted(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record("kept"), myfuture_record("gone")])

    UpsertMyFutureJobPostings(records=[myfuture_record("kept")])

    assert list(JobPosting.objects.values_list("external_id", flat=True)) == ["kept"]


def test_an_unpublished_offer_myfuture_no_longer_lists_is_deleted(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record()])
    JobPosting.objects.update(hidden=True)

    UpsertMyFutureJobPostings(records=[])

    assert not JobPosting.all_objects.exists()


def test_an_offer_that_lost_its_last_category_is_deleted(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record()])

    UpsertMyFutureJobPostings(records=[myfuture_record(internshipTypes=["visit"])])

    assert not JobPosting.objects.exists()


def test_an_offer_that_cannot_be_read_leaves_the_batches_before_it_unwritten(myfuture_record):
    """The offers are written a batch at a time, but all of them or none."""
    with (
        patch("techpourtoutes.utils.job_posting.BATCH_SIZE", 1),
        pytest.raises(KeyError),
    ):
        UpsertMyFutureJobPostings(records=iter([myfuture_record("a"), {"_id": "b"}]))

    assert not JobPosting.objects.exists()


def test_the_other_sources_offers_are_left_alone(myfuture_record):
    JobPosting(
        source=JobPosting.Source.APEC,
        external_id="apec-1",
        title="Développeuse",
        company_name="Apec",
        description="…",
        city="Paris",
        domains=[JobPosting.Domain.DEVELOPPEMENT],
        category=Category.FIRST_JOB,
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        url="https://www.apec.fr/offre/1",
    ).save()

    UpsertMyFutureJobPostings(records=[myfuture_record()])

    assert JobPosting.objects.filter(source=JobPosting.Source.APEC).exists()


def _period(*, days_from_now):
    """A week-long period ending that many days from now, spelled as MyFuture does."""
    end = timezone.now() + timedelta(days=days_from_now)
    return {
        "from": (end - timedelta(days=4)).isoformat().replace("+00:00", "Z"),
        "to": end.isoformat().replace("+00:00", "Z"),
    }


def test_the_details_shown_on_the_posting_page_are_imported(myfuture_record):
    record = myfuture_record(
        nafCode="4321A", secteurOcapiat="Secteur agricole - Services associés"
    )

    UpsertMyFutureJobPostings(records=[record])

    posting = JobPosting.objects.get()
    assert posting.street == "CURATS, LD CANTIRAN"
    # Ocapiat's sector is the branch it follows, not the company's trade: only NAF tells that.
    assert posting.sector == "Travaux d'installation électrique dans tous locaux"
    assert (posting.experience_level, posting.salary) == ("", "")


def test_an_offer_without_a_street_or_a_sector_is_imported(myfuture_record):
    record = myfuture_record(address={"postalCode": "32110", "city": "Caupenne-d'Armagnac"})

    UpsertMyFutureJobPostings(records=[record])

    posting = JobPosting.objects.get()
    assert (posting.street, posting.sector) == ("", "")


def test_an_offer_without_a_period_has_no_dates(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record()])

    posting = JobPosting.objects.get()
    assert (posting.starts_on, posting.ends_on) == (None, None)


def test_the_dates_are_those_of_the_next_period_not_yet_over(myfuture_record):
    periods = [
        _period(days_from_now=40),
        _period(days_from_now=-10),
        _period(days_from_now=2),
    ]

    UpsertMyFutureJobPostings(records=[myfuture_record(periods=periods)])

    posting = JobPosting.objects.get()
    today = timezone.localdate()
    assert (posting.starts_on, posting.ends_on) == (
        today - timedelta(days=2),
        today + timedelta(days=2),
    )


def test_an_offer_whose_naf_code_is_unknown_has_no_sector(myfuture_record):
    UpsertMyFutureJobPostings(records=[myfuture_record(nafCode="9999Z")])

    assert JobPosting.objects.get().sector == ""


def test_the_street_is_spaced_with_plain_single_spaces(myfuture_record):
    """Words glued by no-break spaces would make the whole street a single word, too wide to
    wrap."""
    street = " Hôtel\xa0de\xa0Région\xa0-\t27  place Jules Guesde "
    record = myfuture_record(
        address={"street": street, "postalCode": "13001", "city": "Marseille"}
    )

    UpsertMyFutureJobPostings(records=[record])

    assert JobPosting.objects.get().street == "Hôtel de Région - 27 place Jules Guesde"
