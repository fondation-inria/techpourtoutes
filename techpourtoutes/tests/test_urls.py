import pytest
from django.urls import get_resolver, reverse

URLCONFS = [
    "techpourtoutes.urls_common",
    "techpourtoutes.urls_beneficiary",
    "techpourtoutes.urls_coalition",
]


@pytest.mark.parametrize("urlconf", URLCONFS)
def test_routes_end_with_a_slash(urlconf):
    """A slash-less route 404s on the slash-terminated URL: APPEND_SLASH never strips one."""
    routes = [str(pattern.pattern) for pattern in get_resolver(urlconf).url_patterns]
    assert [route for route in routes if route and not route.endswith("/")] == []


@pytest.mark.django_db
def test_legacy_home_page_redirects_permanently_to_home(client):
    response = client.get("/page-d-accueil-techpourtoutes-992956", follow=True)

    assert response.redirect_chain[-1] == ("/", 301)


@pytest.mark.django_db
def test_legacy_sign_up_page_redirects_permanently_to_beneficiary_inscription_funnel(client):
    response = client.get("/pour-s-inscrire-c-est-juste-ici-532220", follow=True)

    assert (reverse("new_beneficiary_inscription_funnel"), 301) in response.redirect_chain
    assert response.redirect_chain[-1] == (reverse("beneficiary_inscription_funnel"), 302)
