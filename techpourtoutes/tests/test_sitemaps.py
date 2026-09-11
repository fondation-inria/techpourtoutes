import pytest
from django.urls import reverse

from techpourtoutes.sitemaps import StaticViewSitemap

# Public, argument-free pages that are deliberately kept out of the sitemap:
# auth/account flows, HTMX partials, form endpoints, and legal/info pages we
# don't want search engines to index. Adding a new public page forces a
# conscious choice — put it in the sitemap or list it here — see the guard test.
SITEMAP_EXCLUDED_URL_NAMES = {
    # HTMX partials
    "search_schools",
    "search_formations",
    "search_addresses",
    "create_saved_event_modal",
    "show_skip_mentoring_signup_modal",
    # Auth / account (private)
    "login_request",
    "login_code",
    "login_to_jobirl",
    "destroy_session",
    "show_account",
    "show_user_info",
    "edit_user",
    "update_user",
    "update_user_communication",
    "show_user",
    "show_user_email",
    "edit_user_email",
    "create_user_email_change",
    "create_user_email_code",
    "show_user_email_verification",
    "update_user_email",
    "new_beneficiary_training_experience",
    "create_beneficiary_training_experience",
    "destroy_user_modal",
    "destroy_user",
    "mentoring_funnel",
    # Form submission endpoints (their GET page is what gets indexed)
    "create_mentor",
    "create_work_ambassador",
    "create_training_ambassador",
    "create_sponsor",
    "create_workshop_request",
    "create_manifeste_signature",
    "create_upcoming_feature_notification",
    # Funnel steps (not landing pages)
    "show_manifeste_signature",
    "coalition_welcome",
    "inscription_funnel",
    "event_funnel",
    # Legal / info (intentionally not indexed)
    "donnees_personnelles",
    "conditions_generales",
    "mentions_legales",
    "accessibilite",
    "schema_pluriannuel",
    "a_propos",
    "new_upcoming_feature_notification",
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

    accounted_for = set(StaticViewSitemap().items()) | SITEMAP_EXCLUDED_URL_NAMES

    app_page_names = _argument_free_names(urls_coalition, urls_common, urls_beneficiary)

    unaccounted = app_page_names - accounted_for
    assert not unaccounted, (
        "New public page(s) not referenced in the sitemap nor excluded: "
        f"{sorted(unaccounted)}. Add them to a sitemap in techpourtoutes.sitemaps "
        "or to SITEMAP_EXCLUDED_URL_NAMES."
    )


@pytest.mark.django_db
def test_beneficiary_sitemap_includes_coalition_pages_served_under_prefix():
    items = StaticViewSitemap().items()
    assert "home" in items
    assert "coalition_home" in items
    assert "new_mentor" in items
    assert len(items) == len(set(items))


@pytest.mark.django_db
def test_sitemap_returns_200(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200


@pytest.mark.django_db
def test_sitemap_contains_public_urls(client):
    content = client.get("/sitemap.xml").content.decode()
    assert reverse("coalition_home") in content
    assert reverse("new_mentor") in content
    assert reverse("notre_manifeste") in content
