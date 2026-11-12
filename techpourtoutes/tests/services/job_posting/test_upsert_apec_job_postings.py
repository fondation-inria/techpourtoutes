from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from techpourtoutes.models import JobPosting
from techpourtoutes.services.job_posting.upsert_apec_job_postings import UpsertApecJobPostings

pytestmark = pytest.mark.django_db

Category = JobPosting.Category
ContractType = JobPosting.ContractType
Domain = JobPosting.Domain

LAST_WEEK = datetime(2026, 10, 27, tzinfo=UTC)


def test_an_offer_is_mapped_onto_a_job_posting(apec_record):
    result = UpsertApecJobPostings(records=[apec_record()])

    assert result.success
    posting = JobPosting.objects.get()
    assert posting.source == JobPosting.Source.APEC
    assert posting.external_id == "179254673W"
    assert posting.title == "Développeur BI F/H"
    assert posting.company_name == "TRANSPORTS DE L'AGGLOMÉRATION"
    assert posting.postal_code == ""
    assert posting.cog_code == "75101"
    assert posting.department_code == "75"
    assert posting.city == "Paris 01"
    assert posting.domains == [JobPosting.Domain.MAITRISE_D_OUVRAGE]
    assert posting.duration_months == 12
    assert posting.company_logo == (
        "https://www.apec.fr/files/live/mounts/images"
        "/media_entreprise/804755/logo_B-HIVE_804755_1282656.png"
    )
    assert posting.category == Category.FIRST_JOB
    assert posting.contract_type == ContractType.CDD
    assert posting.published_at == datetime(
        2026, 8, 11, 16, 39, 57, tzinfo=ZoneInfo("Europe/Paris")
    )
    assert posting.source_updated_at is None
    assert posting.url == (
        "https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/179254673W"
        "?xtor=#at_medium=affiliate&at_campaign=Export_offres_techpourtoutes"
        "&at_type=partenaire_export"
    )


@pytest.mark.parametrize(
    ("city", "titleized"),
    [
        ("ST JULIEN EN GENEVOIS", "St Julien En Genevois"),
        ("AIX EN PROVENCE", "Aix En Provence"),
        ("Etats-Unis", "Etats-Unis"),
    ],
)
def test_the_city_is_titleized(apec_record, city, titleized):
    UpsertApecJobPostings(records=[apec_record(Libelle_lieu=city)])

    assert JobPosting.objects.get().city == titleized


def test_the_title_and_the_company_lose_their_html_entities_and_stray_spaces(apec_record):
    record = apec_record(
        Intitule="Ingénieur  DevOps F/H ", Nom_entreprise=" CRIT PARIS Banque &amp; Finance"
    )

    UpsertApecJobPostings(records=[record])

    posting = JobPosting.objects.get()
    assert posting.title == "Ingénieur DevOps F/H"
    assert posting.company_name == "CRIT PARIS Banque & Finance"


def test_an_offer_without_a_duration_or_a_logo_is_imported(apec_record):
    record = apec_record()
    del record["Duree_contrat"], record["Logo_entreprise"]

    UpsertApecJobPostings(records=[record])

    posting = JobPosting.objects.get()
    assert posting.duration_months is None
    assert posting.company_logo == ""


@pytest.mark.parametrize(
    ("contract", "category", "contract_type"),
    [
        ("CDI", Category.FIRST_JOB, ContractType.CDI),
        ("CDD", Category.FIRST_JOB, ContractType.CDD),
        ("Mission d'intérim", Category.FIRST_JOB, ContractType.INTERIM),
        ("Stage", Category.HIGHER_ED_INTERNSHIP, ""),
        (
            "CDD - Alternance - Contrat d'apprentissage",
            Category.APPRENTICESHIP,
            ContractType.APPRENTICESHIP,
        ),
        (
            "CDI - Alternance - Contrat d'apprentissage",
            Category.APPRENTICESHIP,
            ContractType.APPRENTICESHIP,
        ),
        (
            "CDD - Alternance - Contrat de professionnalisation",
            Category.APPRENTICESHIP,
            ContractType.PROFESSIONALIZATION,
        ),
    ],
)
def test_each_contract_lands_in_its_category(apec_record, contract, category, contract_type):
    UpsertApecJobPostings(records=[apec_record(Type_contrat=contract)])

    posting = JobPosting.objects.get()
    assert posting.category == category
    assert posting.contract_type == contract_type


@pytest.mark.parametrize(
    "experience",
    [
        "Aucune expérience exigée",
        "Tous niveaux d'expérience acceptés",
        "Minimum 1 an",
        "Minimum 2 ans",
        "Minimum 3 ans",
    ],
)
def test_an_offer_asking_up_to_three_years_is_imported(apec_record, experience):
    UpsertApecJobPostings(records=[apec_record(Niveau_experience=experience)])

    assert JobPosting.objects.exists()


@pytest.mark.parametrize("experience", ["Minimum 4 ans", "Minimum 5 ans", "Minimum 10 ans", None])
def test_an_offer_asking_more_than_three_years_or_unknown_is_not_imported(apec_record, experience):
    """A level Apec would add or rename is left out until we decide where it belongs."""
    UpsertApecJobPostings(records=[apec_record(Niveau_experience=experience)])

    assert not JobPosting.objects.exists()


@pytest.mark.parametrize(
    ("function", "domain"),
    [
        ("02B", Domain.CREATION),
        ("04A", Domain.CONCEPTION_RECHERCHE),
        ("04B", Domain.DIRECTION_RECHERCHE_DEVELOPPEMENT),
        ("04D", Domain.PROJETS_SCIENTIFIQUES_TECHNIQUES),
        ("04E", Domain.TEST_ESSAI_VALIDATION_EXPERTISE),
        ("06A", Domain.INFORMATIQUE),
        ("06B", Domain.EXPLOITATION_MAINTENANCE),
        ("06C", Domain.INFORMATIQUE_DE_GESTION),
        ("06D", Domain.INFORMATIQUE_INDUSTRIELLE),
        ("06E", Domain.DEVELOPPEMENT),
        ("06F", Domain.MAITRISE_D_OUVRAGE),
        ("06G", Domain.SYSTEMES_ET_RESEAUX),
    ],
)
def test_each_function_we_follow_lands_in_its_domain(apec_record, function, domain):
    UpsertApecJobPostings(records=[apec_record(JOB_fonction=function)])

    assert JobPosting.objects.get().domains == [domain]


@pytest.mark.parametrize("function", ["01C", "04C", "05F", "07A", "08B", "10D"])
def test_the_other_functions_are_not_imported(apec_record, function):
    UpsertApecJobPostings(records=[apec_record(JOB_fonction=function)])

    assert not JobPosting.objects.exists()


def test_the_description_keeps_its_layout_but_loses_whatever_could_run(apec_record):
    record = apec_record(
        Texte_offre=(
            '<h2 style="color: red">Missions</h2>'
            '<p title="autre">D&eacute;veloppeur</p><script>steal()</script>'
        )
    )

    UpsertApecJobPostings(records=[record])

    assert JobPosting.objects.get().description == "<h2>Missions</h2><p>Développeur</p>"


@pytest.mark.parametrize(
    ("section", "heading"),
    [
        ("description_offre", "Détail du poste"),
        ("profil", "Profil recherché"),
        ("presentation_entreprise", "M&amp;J Conseil"),
    ],
)
def test_each_titled_paragraph_is_replaced_by_its_heading(apec_record, section, heading):
    record = apec_record(
        Nom_entreprise="M&amp;J  Conseil",
        Texte_offre=f'<p title="{section}"><p>Du texte</p></p>',
    )

    UpsertApecJobPostings(records=[record])

    assert JobPosting.objects.get().description == f"<h3>{heading}</h3><p>Du texte</p>"


def test_a_titled_paragraph_holding_its_text_keeps_it_as_a_paragraph(apec_record):
    """One section in seven or so holds its text directly rather than in paragraphs of its own."""
    UpsertApecJobPostings(records=[apec_record(Texte_offre='<p title="profil">Curieuse</p>')])

    assert JobPosting.objects.get().description == "<h3>Profil recherché</h3><p>Curieuse</p>"


def test_the_description_keeps_its_divisions_and_bold_text(apec_record):
    """Some sections are written in divisions rather than paragraphs, some in `<b>`."""
    record = apec_record(
        Texte_offre=(
            '<p title="presentation_entreprise"><div class="ql-align-justify">Depuis '
            "<b>2002</b>.</div><div>Avec 220 personnes.</div></p>"
        )
    )

    UpsertApecJobPostings(records=[record])

    assert JobPosting.objects.get().description == (
        "<h3>TRANSPORTS DE L'AGGLOMÉRATION</h3>"
        "<div>Depuis <b>2002</b>.</div><div>Avec 220 personnes.</div>"
    )


def test_the_description_shows_the_line_breaks_typed_in_the_text(apec_record):
    record = apec_record(Texte_offre='<p title="profil">Formation en électricité\nPermis B</p>')

    UpsertApecJobPostings(records=[record])

    assert JobPosting.objects.get().description == (
        "<h3>Profil recherché</h3><p>Formation en électricité<br>Permis B</p>"
    )


def test_an_offer_already_imported_is_updated_in_place(apec_record):
    UpsertApecJobPostings(records=[apec_record()])
    first_pk = JobPosting.objects.get().pk

    UpsertApecJobPostings(records=[apec_record(Intitule="Data Engineer F/H")])

    posting = JobPosting.objects.get()
    assert posting.pk == first_pk
    assert posting.title == "Data Engineer F/H"


def test_an_offer_the_export_lists_unchanged_keeps_its_update_date(apec_record):
    UpsertApecJobPostings(records=[apec_record()])
    JobPosting.objects.update(updated_at=LAST_WEEK)

    UpsertApecJobPostings(records=[apec_record()])

    assert JobPosting.objects.get().updated_at == LAST_WEEK


def test_an_offer_published_in_the_hour_that_repeats_in_october_keeps_its_update_date(
    apec_record,
):
    """2:05 a.m. comes twice the night clocks go back: still the same instant once stored."""
    UpsertApecJobPostings(records=[apec_record(Date_parution="25/10/2026 02:05:30")])
    JobPosting.objects.update(updated_at=LAST_WEEK)

    UpsertApecJobPostings(records=[apec_record(Date_parution="25/10/2026 02:05:30")])

    assert JobPosting.objects.get().updated_at == LAST_WEEK


def test_an_offer_that_changed_moves_its_update_date(apec_record):
    UpsertApecJobPostings(records=[apec_record()])
    JobPosting.objects.update(updated_at=LAST_WEEK)

    UpsertApecJobPostings(records=[apec_record(Intitule="Data Engineer F/H")])

    assert JobPosting.objects.get().updated_at > timezone.now() - timedelta(minutes=1)


def test_an_offer_unpublished_by_hand_stays_unpublished_once_updated(apec_record):
    UpsertApecJobPostings(records=[apec_record()])
    JobPosting.objects.update(hidden=True)

    UpsertApecJobPostings(records=[apec_record(Intitule="Data Engineer F/H")])

    posting = JobPosting.all_objects.get()
    assert posting.title == "Data Engineer F/H"
    assert posting.hidden


def test_an_offer_the_export_no_longer_lists_is_deleted(apec_record):
    UpsertApecJobPostings(records=[apec_record("kept"), apec_record("gone")])

    UpsertApecJobPostings(records=[apec_record("kept")])

    assert list(JobPosting.objects.values_list("external_id", flat=True)) == ["kept"]


def test_an_offer_now_asking_too_much_experience_is_deleted(apec_record):
    UpsertApecJobPostings(records=[apec_record("kept"), apec_record("gone")])

    UpsertApecJobPostings(
        records=[apec_record("kept"), apec_record("gone", Niveau_experience="Minimum 5 ans")]
    )

    assert list(JobPosting.objects.values_list("external_id", flat=True)) == ["kept"]


@pytest.mark.parametrize(
    "records",
    [[], [{"JOB_fonction": "01C", "Niveau_experience": "Minimum 1 an"}]],
    ids=["no offer", "no offer kept"],
)
def test_an_export_without_any_offer_to_keep_fails_and_deletes_nothing(apec_record, records):
    """Apec renaming a tag or its function codes must not read as every offer withdrawn."""
    UpsertApecJobPostings(records=[apec_record()])

    result = UpsertApecJobPostings(records=records)

    assert result.failure
    assert JobPosting.objects.count() == 1


def test_an_offer_that_cannot_be_read_leaves_the_batches_before_it_unwritten(apec_record):
    """The offers are written a batch at a time, but all of them or none."""
    with (
        patch("techpourtoutes.utils.job_posting.BATCH_SIZE", 1),
        pytest.raises(KeyError),
    ):
        UpsertApecJobPostings(records=iter([apec_record("a"), {"Niveau_experience": None}]))

    assert not JobPosting.objects.exists()


def test_the_other_sources_offers_are_left_alone(apec_record):
    JobPosting(
        source=JobPosting.Source.MYFUTURE,
        external_id="22NisRqehckrMvEu3",
        title="Stage en électricité générale",
        company_name="Didier Ducom",
        description="…",
        city="Caupenne-d'Armagnac",
        domains=[JobPosting.Domain.ELECTROTECHNIQUE],
        category=Category.TROISIEME_INTERNSHIP,
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        url="https://myfutu.re/internships/offers/22NisRqehckrMvEu3",
    ).save()

    UpsertApecJobPostings(records=[apec_record()])

    assert JobPosting.objects.filter(source=JobPosting.Source.MYFUTURE).exists()


def test_the_details_shown_on_the_posting_page_are_imported(apec_record):
    UpsertApecJobPostings(records=[apec_record()])

    posting = JobPosting.objects.get()
    assert posting.experience_level == "Minimum 3 ans"
    assert posting.salary == "A partir de 38 k€ brut annuel"
    assert posting.sector == "Transports urbains et suburbains de voyageurs"
    assert posting.street == ""
    assert posting.starts_on is None


def test_the_sector_is_the_insee_label_of_the_naf_code(apec_record):
    record = apec_record(
        NAF_secteur="7810Z",
        Libelle_secteur="ACTIVITÉS DES AGENCES DE PLACEMENT DE MAIN-D'OEUVRE",
    )

    UpsertApecJobPostings(records=[record])

    assert JobPosting.objects.get().sector == "Activités des agences de placement de main-d'œuvre"


def test_an_offer_without_a_salary_or_sector_is_imported(apec_record):
    record = apec_record()
    del record["Salaire_affiche"], record["NAF_secteur"]

    UpsertApecJobPostings(records=[record])

    posting = JobPosting.objects.get()
    assert (posting.salary, posting.sector) == ("", "")
