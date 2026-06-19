import pytest
from django.test import override_settings
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
    "signature_manifeste",
]


@pytest.mark.parametrize("url_name", LEGAL_URL_NAMES + A_PROPOS_URL_NAMES)
def test_static_page_returns_200(client, url_name):
    assert client.get(reverse(url_name)).status_code == 200


@override_settings(SITE_URL="https://example.test")
def test_signature_manifeste_linkedin_share_url(client):
    response = client.get(reverse("signature_manifeste"))
    assert response.context["linkedin_share_url"] == (
        "https://www.linkedin.com/sharing/share-offsite/?url=https://example.test/notre-manifeste/"
    )


@pytest.mark.parametrize("url_name", LEGAL_URL_NAMES)
@override_settings(SITE_URL="https://example.test")
def test_static_page_renders_site_url(client, url_name):
    response = client.get(reverse(url_name))
    assert response.context["site_url"] == "https://example.test"
    assert b"https://example.test" in response.content


def test_a_propos_redirects_to_notre_manifeste(client):
    response = client.get(reverse("a_propos"))
    assert response.status_code == 302
    assert response.url == reverse("notre_manifeste")
