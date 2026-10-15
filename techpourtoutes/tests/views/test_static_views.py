import re
from urllib.parse import urlsplit

import pytest
from django.urls import resolve, reverse

from techpourtoutes.tests.sitemap_exclusions import NEVER_LISTED_URL_NAMES, argument_free_url_names

LEGAL_URL_NAMES = [
    "donnees_personnelles",
    "conditions_generales",
    "mentions_legales",
    "accessibilite",
    "schema_pluriannuel",
]

INFORMATIONS_LEGALES_URL_NAMES = [
    "mentions_legales",
    "conditions_generales",
    "donnees_personnelles",
]

A_PROPOS_URL_NAMES = [
    "notre_manifeste",
    "qui_sommes_nous",
    "pourquoi_nous_ecrivons_au_feminin",
    "contact",
]

# Pages the HTML sitemap leaves out on top of the NEVER_LISTED_URL_NAMES: it mirrors what the
# navigation offers everyone. Adding a new page forces a conscious choice — link it from the
# HTML sitemap or list it here — see the guard test.
HTML_SITEMAP_EXCLUDED_URL_NAMES = {
    # Not linked from the navigation
    "new_manifeste_signature",
    # The HTML sitemap itself
    "html_sitemap",
}


def _html_sitemap_url_names(client):
    main = client.get(reverse("html_sitemap")).content.decode().split("<main", 1)[1]
    hrefs = re.findall(r'href="([^"]+)"', main.split("</main>", 1)[0])
    return {resolve(urlsplit(href).path).url_name for href in hrefs}


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", LEGAL_URL_NAMES + A_PROPOS_URL_NAMES + ["html_sitemap"])
def test_static_page_returns_200(client, url_name):
    assert client.get(reverse(url_name)).status_code == 200


@pytest.mark.django_db
def test_a_propos_redirects_to_notre_manifeste(client):
    response = client.get(reverse("a_propos"))
    assert response.status_code == 302
    assert response.url == reverse("notre_manifeste")


@pytest.mark.django_db
def test_informations_legales_redirects_to_mentions_legales(client):
    response = client.get(reverse("informations_legales"))
    assert response.status_code == 302
    assert response.url == reverse("mentions_legales")


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", INFORMATIONS_LEGALES_URL_NAMES)
def test_informations_legales_page_links_every_tab(client, url_name):
    content = client.get(reverse(url_name)).content.decode()
    for tab in INFORMATIONS_LEGALES_URL_NAMES:
        assert f'href="{reverse(tab)}" role="tab"' in content


@pytest.mark.django_db
def test_footer_links_to_informations_legales_instead_of_each_legal_page(client):
    footer = client.get(reverse("home")).content.decode().split("<footer", 1)[1]
    assert f'href="{reverse("informations_legales")}"' in footer
    for url_name in INFORMATIONS_LEGALES_URL_NAMES:
        assert f'href="{reverse(url_name)}"' not in footer


@pytest.mark.django_db
def test_html_sitemap_links_every_page_not_explicitly_excluded(client):
    listed = (
        _html_sitemap_url_names(client) | NEVER_LISTED_URL_NAMES | HTML_SITEMAP_EXCLUDED_URL_NAMES
    )

    unaccounted = argument_free_url_names() - listed
    assert not unaccounted, (
        f"Page(s) neither linked from the HTML sitemap nor excluded: {sorted(unaccounted)}. "
        "Link them from static/html_sitemap.html, add them to HTML_SITEMAP_EXCLUDED_URL_NAMES, "
        "or to NEVER_LISTED_URL_NAMES if no sitemap should list them (HTMX partial, form "
        "endpoint, funnel step…)."
    )


@pytest.mark.django_db
def test_html_sitemap_is_linked_from_the_footer(client):
    assert f'href="{reverse("html_sitemap")}"' in client.get(reverse("home")).content.decode()
