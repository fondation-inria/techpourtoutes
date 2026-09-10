import pytest
from django.urls import reverse

LEGAL_URL_NAMES = [
    "donnees_personnelles",
    "conditions_generales",
    "mentions_legales",
    "accessibilite",
    "schema_pluriannuel",
]

A_PROPOS_URL_NAMES = [
    "notre_manifeste",
    "qui_sommes_nous",
    "pourquoi_nous_ecrivons_au_feminin",
    "contact",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", LEGAL_URL_NAMES + A_PROPOS_URL_NAMES)
def test_static_page_returns_200(client, url_name):
    assert client.get(reverse(url_name)).status_code == 200


@pytest.mark.django_db
def test_a_propos_redirects_to_notre_manifeste(client):
    response = client.get(reverse("a_propos"))
    assert response.status_code == 302
    assert response.url == reverse("notre_manifeste")
