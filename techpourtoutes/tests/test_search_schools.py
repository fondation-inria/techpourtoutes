import pytest
from django.urls import reverse


@pytest.fixture
def schools(db):
    from techpourtoutes.models import School

    School(identifier="0750001A", name="Lycée Voltaire", postal_code="75011").save()
    School(identifier="0690002B", name="Collège Jean Moulin", postal_code="69003").save()
    School(identifier="0750003C", name="Lycée Henri IV", postal_code="75005").save()
    School(identifier="0440004D", name="Lycée privée La Providence", postal_code="44000").save()


@pytest.mark.django_db
def test_search_schools_matches_by_name(client, schools):
    response = client.get(reverse("search_schools"), {"q": "voltaire"})
    assert response.status_code == 200
    content = response.content.decode()
    assert "Lycée Voltaire" in content
    assert "Collège Jean Moulin" not in content


@pytest.mark.django_db
def test_search_schools_matches_by_postal_code(client, schools):
    response = client.get(reverse("search_schools"), {"q": "750"})
    content = response.content.decode()
    assert "Lycée Voltaire" in content
    assert "Lycée Henri IV" in content
    assert "Collège Jean Moulin" not in content


@pytest.mark.django_db
def test_search_schools_multi_word_is_order_independent(client, schools):
    response = client.get(reverse("search_schools"), {"q": "lycée la providence"})
    content = response.content.decode()
    assert "Lycée privée La Providence" in content
    assert "Lycée Voltaire" not in content


@pytest.mark.django_db
def test_search_schools_is_accent_insensitive(client, schools):
    response = client.get(reverse("search_schools"), {"q": "providence lycee privee"})
    content = response.content.decode()
    assert "Lycée privée La Providence" in content
    assert "Lycée Voltaire" not in content


@pytest.mark.django_db
def test_search_schools_empty_query_returns_first_page(client, schools):
    response = client.get(reverse("search_schools"), {"q": ""})
    content = response.content.decode()
    assert "Lycée Voltaire" in content
    assert "Collège Jean Moulin" in content


@pytest.mark.django_db
def test_school_search_escapes_reflected_value_for_js_context(client):
    # On a failed POST the form re-renders with the submitted structure_name interpolated
    # into the Alpine x-data JS strings. escapejs emits ' for a single quote (safe in
    # the JS context); plain HTML autoescaping would emit &#x27; which the browser decodes
    # back to a real quote, breaking out of the string.
    response = client.post(
        reverse("training_ambassador_landing"),
        {"structure_name": "Test'X"},
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Test\\u0027X" in content
    assert "Test&#x27;X" not in content


@pytest.mark.django_db
def test_search_schools_paginates_with_next_page_sentinel(client):
    from techpourtoutes.models import School

    for i in range(25):
        School(identifier=f"E{i:04d}", name=f"Lycée {i:02d}", postal_code="75001").save()

    first = client.get(reverse("search_schools"), {"q": "lycée"}).content.decode()
    assert first.count("hover:bg-primary-50") == 20
    assert "page=2" in first

    second = client.get(reverse("search_schools"), {"q": "lycée", "page": "2"}).content.decode()
    assert second.count("hover:bg-primary-50") == 5
    assert "page=3" not in second
