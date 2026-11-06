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


def _save_searchable_posting(title="Stage", **overrides):
    save_job_posting(title, JobPosting.Category.HIGHER_ED_INTERNSHIP, **overrides)


def _titles_found_by(terms):
    return [job_posting.title for job_posting in JobPosting.objects.search(terms)]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field", ["title", "company_name", "description"], ids=["title", "company", "description"]
)
def test_search_looks_into_the_title_the_company_and_the_description(field):
    _save_searchable_posting(**{field: "Cybersécurité"})
    _save_searchable_posting("Autre stage")

    assert len(_titles_found_by("cybersécurité")) == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "terms",
    ["developpeur", "DÉVELOPPEUR", "dév", "développeuse", "développeurs"],
    ids=["no_accent", "uppercase", "start_of_a_word", "feminine", "plural"],
)
def test_search_finds_a_word_however_it_is_typed(terms):
    _save_searchable_posting("Développeur web")

    assert _titles_found_by(terms) == ["Développeur web"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "feminine, masculine",
    [
        ("développeuse", "développeur"),
        ("Développeuses", "développeurs"),
        ("chercheuse", "chercheur"),
        ("testeuse", "testeur"),
        ("programmeuse", "programmeur"),
        ("conductrice", "conducteur"),
        ("directrice", "directeur"),
        ("formatrices", "formateurs"),
        ("cheffe", "chef"),
        ("cheffes", "chefs"),
        ("chargée", "chargé"),
        ("ingénieure", "ingénieur"),
        ("informaticienne", "informaticien"),
        ("consultante", "consultant"),
    ],
)
def test_search_finds_the_same_postings_in_the_feminine_and_the_masculine(feminine, masculine):
    _save_searchable_posting(f"Poste de {masculine}")
    _save_searchable_posting(f"Poste de {feminine}")
    _save_searchable_posting("Autre poste", description="Rien à voir")

    expected = {f"Poste de {masculine}", f"Poste de {feminine}"}
    assert set(_titles_found_by(feminine)) == expected
    assert set(_titles_found_by(masculine)) == expected


@pytest.mark.django_db
@pytest.mark.parametrize("terms", ["développeuse", "développeur"])
@pytest.mark.parametrize(
    "field", ["title", "company_name", "description"], ids=["title", "company", "description"]
)
def test_search_finds_a_posting_written_in_the_feminine_in_any_field(field, terms):
    _save_searchable_posting(**{field: "DÉVELOPPEUSE web"})

    assert len(_titles_found_by(terms)) == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "word", ["Matrice", "Matrices", "Motrice", "Creuse", "Meuse", "rigoureuse"]
)
def test_search_still_finds_the_words_which_only_look_feminine(word):
    _save_searchable_posting(word)

    assert _titles_found_by(word) == [word]


@pytest.mark.django_db
@pytest.mark.parametrize("feminine", ["développeuse", "programmeuse"])
def test_search_in_the_feminine_leaves_out_the_words_of_the_same_family(feminine):
    _save_searchable_posting("Développement web")
    _save_searchable_posting("Programmation")

    assert _titles_found_by(feminine) == []


@pytest.mark.django_db
def test_search_requires_every_word():
    _save_searchable_posting("Développeur web")
    _save_searchable_posting("Développeur mobile")

    assert _titles_found_by("développeur mobile") == ["Développeur mobile"]


@pytest.mark.django_db
def test_search_finds_a_dotted_name_however_it_is_spelled():
    _save_searchable_posting("Développeur Node.js")
    _save_searchable_posting("Développeur NodeJS")
    _save_searchable_posting("Développeur Node JS")
    _save_searchable_posting("Développeur Java")

    assert set(_titles_found_by("node.js")) == {
        "Développeur Node.js",
        "Développeur NodeJS",
        "Développeur Node JS",
    }


@pytest.mark.django_db
def test_search_leaves_out_the_parts_of_a_dotted_name_far_apart():
    _save_searchable_posting("Stage Vue.js")
    _save_searchable_posting("Stage avec vue sur la mer", description="Début en juin")

    assert _titles_found_by("vue.js") == ["Stage Vue.js"]


@pytest.mark.django_db
@pytest.mark.parametrize("terms", ["c++ & (web", "d'alternance", "web:* | !", "'\\", "\x00web"])
def test_search_does_not_break_on_punctuation(terms):
    _save_searchable_posting("Développeur web")

    list(JobPosting.objects.search(terms))


@pytest.mark.django_db
def test_search_ranks_the_title_above_the_company_above_the_description():
    _save_searchable_posting("Dans la description", description="Un poste de cybersécurité")
    _save_searchable_posting("Dans l'entreprise", company_name="Cybersécurité SA")
    _save_searchable_posting("Cybersécurité")

    found = JobPosting.objects.search("cybersécurité").order_by("-relevance")

    assert [job_posting.title for job_posting in found] == [
        "Cybersécurité",
        "Dans l'entreprise",
        "Dans la description",
    ]
