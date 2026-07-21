import pytest
from django.urls import reverse
from waffle.testutils import override_switch

from techpourtoutes.sitemaps import StaticViewSitemap

# Public, argument-free pages that are deliberately kept out of the sitemap:
# auth/account flows, HTMX partials, form endpoints, and legal/info pages we
# don't want search engines to index. Adding a new public page forces a
# conscious choice — put it in the sitemap or list it here — see the guard test.
SITEMAP_EXCLUDED_URL_NAMES = {
    # HTMX partials
    "search_schools",
    "search_higher_ed_schools",
    # Auth / account (private)
    "login_request",
    "login_email_sent",
    "login_to_jobirl",
    "logout",
    "account",
    "account_info",
    "account_edit",
    "account_communication",
    "account_email",
    "email_change",
    "email_change_resend",
    "email_change_verify",
    "delete_account_modal",
    "delete_account",
    # Funnel steps (not landing pages)
    "signature_manifeste",
    "coalition_welcome",
    # Legal / info (intentionally not indexed)
    "donnees_personnelles",
    "conditions_generales",
    "mentions_legales",
    "accessibilite",
    "schema_pluriannuel",
    "a_propos",
}


def _argument_free_names(*url_modules):
    return {
        pattern.name
        for module in url_modules
        for pattern in module.urlpatterns
        if pattern.name and not pattern.pattern.converters
    }


@pytest.mark.django_db
def test_every_public_page_is_either_in_sitemap_or_explicitly_excluded():
    from techpourtoutes import urls_beneficiary, urls_coalition, urls_common

    coalition_sitemap = set(StaticViewSitemap().items())
    with override_switch("beneficiary_mode", active=True):
        beneficiary_sitemap = set(StaticViewSitemap().items())
    accounted_for = coalition_sitemap | beneficiary_sitemap | SITEMAP_EXCLUDED_URL_NAMES

    app_page_names = _argument_free_names(urls_coalition, urls_common, urls_beneficiary)

    unaccounted = app_page_names - accounted_for
    assert not unaccounted, (
        "New public page(s) not referenced in the sitemap nor excluded: "
        f"{sorted(unaccounted)}. Add them to a sitemap in techpourtoutes.sitemaps "
        "or to SITEMAP_EXCLUDED_URL_NAMES."
    )


@pytest.mark.django_db
def test_beneficiary_sitemap_includes_coalition_pages_served_under_prefix():
    with override_switch("beneficiary_mode", active=True):
        items = StaticViewSitemap().items()
    assert "home" in items
    assert "coalition_home" in items
    assert "mentor_landing" in items
    assert len(items) == len(set(items))


@pytest.mark.django_db
def test_robots_txt_returns_200(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain"


@pytest.mark.django_db
def test_robots_txt_content(client):
    content = client.get("/robots.txt").content.decode()
    assert "User-agent: *" in content
    assert "Sitemap:" in content
    assert "/sitemap.xml" in content


@pytest.mark.django_db
def test_robots_txt_disallows_private_pages(client):
    content = client.get("/robots.txt").content.decode()
    assert "Disallow: /mon-compte/" in content
    assert "Disallow: /mon-compte-mentor/" in content
    assert "Disallow: /bienvenue-dans-la-coalition/" in content


@pytest.mark.django_db
def test_sitemap_returns_200(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200


@pytest.mark.django_db
def test_sitemap_contains_public_urls(client):
    content = client.get("/sitemap.xml").content.decode()
    assert reverse("coalition_home") in content
    assert reverse("mentor_landing") in content
    assert reverse("notre_manifeste") in content


@pytest.mark.django_db
def test_home_page_has_unique_title(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert "<title>TechPourToutes</title>" not in content
    assert "<title>" in content


@pytest.mark.django_db
def test_home_page_has_meta_description(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert 'name="description"' in content


@pytest.mark.django_db
def test_base_template_has_lang_fr(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert 'lang="fr"' in content


@pytest.mark.django_db
def test_base_template_has_canonical(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert 'rel="canonical"' in content


@pytest.mark.django_db
def test_base_template_has_og_tags(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert 'property="og:title"' in content
    assert 'property="og:url"' in content
    assert 'property="og:image"' in content


@pytest.mark.django_db
def test_default_og_image_uses_coalition_cover(client):
    content = client.get(reverse("coalition_home")).content.decode()
    assert "coalition-tpt-white.png" in content


@pytest.mark.django_db
def test_notre_manifeste_og_image_uses_manifeste_cover(client):
    content = client.get(reverse("notre_manifeste")).content.decode()
    assert "manifeste-tpt-cover-white.png" in content
