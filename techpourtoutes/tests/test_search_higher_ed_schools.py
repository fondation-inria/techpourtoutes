import pytest
from django.urls import reverse


@pytest.fixture
def higher_ed_schools(db):
    from techpourtoutes.models import HigherEdSchool

    HigherEdSchool(full_name="Université de Technologie de Troyes", name="UTT").save()
    HigherEdSchool(full_name="École polytechnique", name="X").save()
    HigherEdSchool(full_name="VetAgro Sup établissement", name="VetAgro Sup").save()


@pytest.mark.django_db
def test_search_higher_ed_schools_matches_by_acronym(client, higher_ed_schools):
    response = client.get(reverse("search_higher_ed_schools"), {"q": "UTT"})
    assert response.status_code == 200
    content = response.content.decode()
    assert "Université de Technologie de Troyes" in content
    assert "École polytechnique" not in content


@pytest.mark.django_db
def test_search_higher_ed_schools_matches_by_full_name(client, higher_ed_schools):
    response = client.get(reverse("search_higher_ed_schools"), {"q": "polytechnique"})
    content = response.content.decode()
    assert "École polytechnique" in content
    assert "Université de Technologie de Troyes" not in content


@pytest.mark.django_db
def test_search_higher_ed_schools_is_accent_insensitive(client, higher_ed_schools):
    response = client.get(reverse("search_higher_ed_schools"), {"q": "ecole polytechnique"})
    content = response.content.decode()
    assert "École polytechnique" in content


@pytest.mark.django_db
def test_search_higher_ed_schools_renders_name_and_full_name_label(client, higher_ed_schools):
    response = client.get(reverse("search_higher_ed_schools"), {"q": "UTT"})
    content = response.content.decode()
    assert "UTT (Université de Technologie de Troyes)" in content


@pytest.mark.django_db
def test_higher_ed_school_search_escapes_reflected_value_for_js_context(client):
    # On a failed POST the form re-renders with the submitted higher_ed_school_label interpolated
    # into the Alpine x-data JS strings. escapejs emits ' for a single quote (safe in
    # the JS context); plain HTML autoescaping would emit &#x27; which the browser decodes
    # back to a real quote, breaking out of the string.
    response = client.post(
        reverse("training_ambassador_landing"),
        {"higher_ed_school_label": "Test'X"},
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Test\\u0027X" in content
    assert "Test&#x27;X" not in content
