import pytest
from django.urls import reverse

from techpourtoutes.models import Formation, FormationAction, School


def search_schools(client, scope, **params):
    return client.get(reverse("search_schools"), {"scope": scope, **params})


def search_formations(client, school, **params):
    return client.get(reverse("search_formations"), {"school_id": str(school.pk), **params})


@pytest.fixture
def schools(db):
    School(onisep_id="1", name="Lycée Voltaire", postal_code="75011", secondary=True).save()
    School(onisep_id="2", name="Collège Jean Moulin", postal_code="69003", secondary=True).save()
    School(onisep_id="3", name="Lycée Henri IV", postal_code="75005", secondary=True).save()
    School(
        onisep_id="4", name="Lycée privée La Providence", postal_code="44000", secondary=True
    ).save()


@pytest.fixture
def higher_ed_schools(db):
    School(
        onisep_id="10", name="Université de Technologie de Troyes", acronym="UTT", higher_ed=True
    ).save()
    School(onisep_id="11", name="École polytechnique", acronym="X", higher_ed=True).save()
    School(
        onisep_id="12",
        name="VetAgro Sup établissement",
        acronym="VetAgro Sup",
        higher_ed=True,
        training_ambassador_eligible=True,
    ).save()


@pytest.mark.django_db
def test_search_without_a_scope_is_rejected(client, schools):
    assert client.get(reverse("search_schools"), {"q": "voltaire"}).status_code == 400


@pytest.mark.django_db
def test_search_with_an_unknown_scope_is_rejected(client, schools):
    assert search_schools(client, "inconnu", q="voltaire").status_code == 400


@pytest.mark.django_db
def test_search_schools_matches_by_name(client, schools):
    response = search_schools(client, "secondary", q="voltaire")

    assert response.status_code == 200
    content = response.content.decode()
    assert "Lycée Voltaire" in content
    assert "Collège Jean Moulin" not in content


@pytest.mark.django_db
def test_search_schools_matches_by_postal_code(client, schools):
    content = search_schools(client, "secondary", q="750").content.decode()

    assert "Lycée Voltaire" in content
    assert "Lycée Henri IV" in content
    assert "Collège Jean Moulin" not in content


@pytest.mark.django_db
def test_search_schools_multi_word_is_order_independent(client, schools):
    content = search_schools(client, "secondary", q="lycée la providence").content.decode()

    assert "Lycée privée La Providence" in content
    assert "Lycée Voltaire" not in content


@pytest.mark.django_db
def test_search_schools_is_accent_insensitive(client, schools):
    content = search_schools(client, "secondary", q="providence lycee privee").content.decode()

    assert "Lycée privée La Providence" in content
    assert "Lycée Voltaire" not in content


@pytest.mark.django_db
def test_search_schools_empty_query_returns_first_page(client, schools):
    content = search_schools(client, "secondary", q="").content.decode()

    assert "Lycée Voltaire" in content
    assert "Collège Jean Moulin" in content


@pytest.mark.django_db
def test_search_schools_renders_the_postal_code(client, schools):
    content = search_schools(client, "secondary", q="voltaire").content.decode()

    assert "Lycée Voltaire (75011)" in content


@pytest.mark.django_db
def test_search_schools_ignores_the_higher_ed_only_schools(client, schools, higher_ed_schools):
    content = search_schools(client, "secondary", q="polytechnique").content.decode()

    assert "École polytechnique" not in content
    assert "Aucun établissement trouvé" in content


@pytest.mark.django_db
def test_search_higher_ed_schools_matches_by_acronym(client, higher_ed_schools):
    response = search_schools(client, "higher_ed", q="UTT")

    assert response.status_code == 200
    content = response.content.decode()
    assert "Université de Technologie de Troyes" in content
    assert "École polytechnique" not in content


@pytest.mark.django_db
def test_search_higher_ed_schools_matches_by_name(client, higher_ed_schools):
    content = search_schools(client, "higher_ed", q="polytechnique").content.decode()

    assert "École polytechnique" in content
    assert "Université de Technologie de Troyes" not in content


@pytest.mark.django_db
def test_search_higher_ed_schools_is_accent_insensitive(client, higher_ed_schools):
    content = search_schools(client, "higher_ed", q="ecole polytechnique").content.decode()

    assert "École polytechnique" in content


@pytest.mark.django_db
def test_search_higher_ed_schools_renders_the_acronym_and_the_name(client, higher_ed_schools):
    content = search_schools(client, "higher_ed", q="UTT").content.decode()

    assert "UTT (Université de Technologie de Troyes)" in content


@pytest.mark.django_db
def test_search_higher_ed_schools_does_not_match_a_postal_code(client, higher_ed_schools):
    School.objects.filter(onisep_id="11").update(postal_code="91120")

    content = search_schools(client, "higher_ed", q="911").content.decode()

    assert "École polytechnique" not in content


@pytest.mark.django_db
def test_training_ambassador_scope_only_offers_the_eligible_schools(client, higher_ed_schools):
    content = search_schools(client, "training_ambassador", q="").content.decode()

    assert "VetAgro Sup" in content
    assert "École polytechnique" not in content


@pytest.mark.django_db
def test_search_schools_paginates_with_next_page_sentinel(client):
    for i in range(25):
        School(onisep_id=str(i), name=f"Lycée {i:02d}", postal_code="75001", secondary=True).save()

    first = search_schools(client, "secondary", q="lycée").content.decode()
    assert first.count("hover:bg-primary-50") == 20
    assert "page=2" in first
    assert "scope=secondary" in first

    second = search_schools(client, "secondary", q="lycée", page="2").content.decode()
    assert second.count("hover:bg-primary-50") == 5
    assert "page=3" not in second


@pytest.mark.django_db
def test_the_sentinel_observes_the_dropdown_it_belongs_to(client):
    for i in range(25):
        School(onisep_id=str(i), name=f"Lycée {i:02d}", secondary=True).save()

    content = search_schools(client, "secondary", q="lycée", unique_id="abc123").content.decode()

    assert "root:#school-results-abc123" in content
    assert "unique_id=abc123" in content


@pytest.mark.django_db
def test_search_formations_without_a_school_is_rejected(client):
    assert client.get(reverse("search_formations"), {"q": "bac"}).status_code == 400


@pytest.mark.django_db
def test_search_formations_with_an_unknown_school_is_rejected(client):
    response = client.get(
        reverse("search_formations"), {"school_id": "00000000-0000-0000-0000-000000000000"}
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_search_formations_only_offers_what_the_school_teaches(client, school):
    taught = Formation(onisep_id="1", name="Bac professionnel")
    taught.save()
    Formation(onisep_id="2", name="Diplôme d'ingénieur").save()
    FormationAction(onisep_id="69395", formation=taught, school=school).save()

    content = search_formations(client, school).content.decode()

    assert "Bac professionnel" in content
    assert "ingénieur" not in content


@pytest.mark.django_db
def test_search_formations_offers_what_the_affiliated_schools_teach(client, higher_ed_school):
    affiliated = School(
        onisep_id="1967",
        name="EFREI Paris - campus de Villejuif",
        parent_onisep_id=higher_ed_school.onisep_id,
        higher_ed=True,
    )
    affiliated.save()
    formation = Formation(onisep_id="1", name="Diplôme d'ingénieur")
    formation.save()
    FormationAction(onisep_id="69395", formation=formation, school=affiliated).save()

    content = search_formations(client, higher_ed_school).content.decode()

    assert "ingénieur" in content


@pytest.mark.django_db
def test_search_formations_falls_back_to_the_whole_catalogue(client, school):
    Formation(onisep_id="1", name="Bac professionnel").save()
    Formation(onisep_id="2", name="Diplôme d'ingénieur").save()

    content = search_formations(client, school).content.decode()

    assert "Bac professionnel" in content
    assert "ingénieur" in content


@pytest.mark.django_db
def test_search_formations_is_accent_insensitive(client, school):
    Formation(onisep_id="1", name="Diplôme d'État d'infirmier").save()

    content = search_formations(client, school, q="diplome etat").content.decode()

    assert "infirmier" in content


@pytest.mark.django_db
def test_search_formations_keeps_an_unmatched_query_empty(client, school):
    taught = Formation(onisep_id="1", name="Bac professionnel")
    taught.save()
    Formation(onisep_id="2", name="Diplôme d'ingénieur").save()
    FormationAction(onisep_id="69395", formation=taught, school=school).save()

    content = search_formations(client, school, q="ingénieur").content.decode()

    assert "ingénieur" not in content
    assert "Aucune formation trouvée" in content


@pytest.mark.django_db
def test_search_formations_paginates_with_next_page_sentinel(client, school):
    for i in range(25):
        Formation(onisep_id=str(i), name=f"Bac professionnel {i:02d}").save()

    first = search_formations(client, school, q="bac").content.decode()
    assert first.count("hover:bg-primary-50") == 20
    assert "page=2" in first
    assert f"school_id={school.pk}" in first

    second = search_formations(client, school, q="bac", page="2").content.decode()
    assert second.count("hover:bg-primary-50") == 5
    assert "page=3" not in second


@pytest.mark.django_db
def test_the_formation_sentinel_observes_the_dropdown_it_belongs_to(client, school):
    for i in range(25):
        Formation(onisep_id=str(i), name=f"Bac professionnel {i:02d}").save()

    content = search_formations(client, school, q="bac", unique_id="abc123").content.decode()

    assert "root:#formation-results-abc123" in content
    assert "unique_id=abc123" in content


@pytest.mark.django_db
def test_school_search_escapes_reflected_value_for_js_context(client):
    # On a failed POST the form re-renders with the submitted structure_name interpolated
    # into the Alpine x-data JS strings. escapejs emits ' for a single quote (safe in
    # the JS context); plain HTML autoescaping would emit &#x27; which the browser decodes
    # back to a real quote, breaking out of the string.
    response = client.post(reverse("workshops_landing"), {"structure_name": "Test'X"})

    assert response.status_code == 200
    content = response.content.decode()
    assert "Test\\u0027X" in content
    assert "Test&#x27;X" not in content


@pytest.mark.django_db
def test_higher_ed_school_search_escapes_reflected_value_for_js_context(client):
    response = client.post(reverse("training_ambassador_landing"), {"school_label": "Test'X"})

    assert response.status_code == 200
    content = response.content.decode()
    assert "Test\\u0027X" in content
    assert "Test&#x27;X" not in content
