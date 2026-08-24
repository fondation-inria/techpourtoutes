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
    "search_formations",
    "mentoring_signup_skip_modal",
    # Auth / account (private)
    "login_request",
    "login_code",
    "login_to_jobirl",
    "logout",
    "account",
    "account_info",
    "account_edit",
    "account_communication",
    "account_detail",
    "account_email",
    "email_change",
    "email_change_resend",
    "email_change_verify",
    "beneficiary_training_experience_add",
    "delete_account_modal",
    "delete_account",
    "add_mentoring",
    # Funnel steps (not landing pages)
    "signature_manifeste",
    "coalition_welcome",
    "inscription_funnel",
    # Legal / info (intentionally not indexed)
    "donnees_personnelles",
    "conditions_generales",
    "mentions_legales",
    "accessibilite",
    "schema_pluriannuel",
    "a_propos",
    "bientot_disponible",
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
def test_sitemap_returns_200(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200


@pytest.mark.django_db
def test_sitemap_contains_public_urls(client):
    content = client.get("/sitemap.xml").content.decode()
    assert reverse("coalition_home") in content
    assert reverse("mentor_landing") in content
    assert reverse("notre_manifeste") in content
