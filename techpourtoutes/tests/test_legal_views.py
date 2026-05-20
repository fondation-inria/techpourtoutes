import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.parametrize(
    "url_name",
    [
        "donnees_personnelles",
        "conditions_generales",
        "mentions_legales",
        "accessibilite",
        "schema_pluriannuel",
    ],
)
def test_legal_page_returns_200(client, url_name):
    assert client.get(reverse(url_name)).status_code == 200


@pytest.mark.parametrize(
    "url_name",
    [
        "donnees_personnelles",
        "conditions_generales",
        "mentions_legales",
        "accessibilite",
        "schema_pluriannuel",
    ],
)
@override_settings(SITE_URL="https://example.test")
def test_legal_page_renders_site_url(client, url_name):
    response = client.get(reverse(url_name))
    assert response.context["site_url"] == "https://example.test"
    assert b"https://example.test" in response.content
