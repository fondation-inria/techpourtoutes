from unittest.mock import patch

import pytest
from django.urls import reverse
from waffle.testutils import override_switch


@pytest.mark.django_db
def test_coalition_home_renders_default_template(client):
    response = client.get(reverse("coalition_home"))
    template_names = [t.name for t in response.templates]
    assert "coalition/coalition_home.html" in template_names


@pytest.mark.django_db
def test_falls_back_to_coalition_mode_when_switch_check_fails(client):
    with patch(
        "techpourtoutes.middleware.switch_is_active",
        side_effect=Exception("waffle unavailable"),
    ):
        response = client.get(reverse("coalition_home"))
    assert response.status_code == 200
    template_names = [t.name for t in response.templates]
    assert "coalition/coalition_home.html" in template_names


@pytest.mark.django_db
def test_coalition_home_renders_beneficiary_home_when_switch_active(client):
    with override_switch("beneficiary_mode", active=True):
        response = client.get(reverse("coalition_home"))
    template_names = [t.name for t in response.templates]
    assert "beneficiary/beneficiary_home.html" in template_names


@pytest.mark.django_db
def test_mentions_legales_shows_coalition_sidebar_by_default(client):
    response = client.get(reverse("mentions_legales"))
    assert "Découvrir le programme" in response.content.decode()


@pytest.mark.django_db
def test_mentions_legales_shows_beneficiary_sidebar_when_switch_active(client):
    with override_switch("beneficiary_mode", active=True):
        response = client.get(reverse("mentions_legales"))
    assert "S'engager" in response.content.decode()


@pytest.mark.django_db
def test_mentor_landing_reachable_at_root_by_default(client):
    assert client.get("/mentorer/").status_code == 200


@pytest.mark.django_db
def test_mentor_landing_not_reachable_under_coalition_prefix_by_default(client):
    assert client.get("/coalition/mentorer/").status_code == 404


@pytest.mark.django_db
def test_mentor_landing_moves_under_coalition_prefix_when_switch_active(client):
    with override_switch("beneficiary_mode", active=True):
        assert client.get("/coalition/mentorer/").status_code == 200


@pytest.mark.django_db
def test_mentor_landing_not_reachable_at_root_when_switch_active(client):
    with override_switch("beneficiary_mode", active=True):
        assert client.get("/mentorer/").status_code == 404


@pytest.mark.django_db
def test_signature_manifeste_moves_under_coalition_prefix_when_switch_active(client):
    with override_switch("beneficiary_mode", active=True):
        assert client.get("/coalition/signature-manifeste/").status_code == 200
        assert client.get("/signature-manifeste/").status_code == 404


@pytest.mark.django_db
def test_search_schools_moves_under_coalition_prefix_when_switch_active(client):
    with override_switch("beneficiary_mode", active=True):
        response = client.get("/coalition/organiser-un-atelier/recherche-etablissements/")
        assert response.status_code == 200


@pytest.mark.django_db
def test_common_pages_stay_at_root_regardless_of_switch(client):
    with override_switch("beneficiary_mode", active=True):
        assert client.get("/se-connecter/").status_code == 200
        assert client.get("/mentions-legales/").status_code == 200


@pytest.mark.django_db
def test_coalition_home_not_reachable_under_coalition_prefix_by_default(client):
    assert client.get("/coalition/").status_code == 404


@pytest.mark.django_db
def test_coalition_home_reachable_under_coalition_prefix_when_switch_active(client):
    with override_switch("beneficiary_mode", active=True):
        response = client.get("/coalition/")
    assert response.status_code == 200
    template_names = [t.name for t in response.templates]
    assert "coalition/coalition_home.html" in template_names
