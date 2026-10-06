import pytest
from django.urls import reverse

from techpourtoutes.sitemaps import StaticViewSitemap
from techpourtoutes.tests.sitemap_exclusions import NEVER_LISTED_URL_NAMES, argument_free_url_names

# Pages the XML sitemap leaves out on top of the NEVER_LISTED_URL_NAMES. Adding a new page
# forces a conscious choice — put it in the XML sitemap or list it here — see the guard test.
XML_SITEMAP_EXCLUDED_URL_NAMES = {
    # Redirects anonymous visitors to the login, which search engines report as an error
    "show_account",
    "show_user_info",
    "edit_user",
    "update_user",
    "update_user_communication",
    "show_user",
    "show_user_email",
    "edit_user_email",
    "show_beneficiary_legal_rep",
    "edit_beneficiary_legal_rep",
    "update_beneficiary_legal_rep",
    "create_user_email_change",
    "create_user_email_code",
    "show_user_email_verification",
    "update_user_email",
    "new_beneficiary_training_experience",
    "create_beneficiary_training_experience",
    "destroy_user_modal",
    "destroy_user",
    "mentoring_funnel",
    "index_pro_events",
    "index_beneficiary_events",
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
    "new_event",
    "create_event",
    "create_event_image_upload",
    "update_event",
    # Legal / info (intentionally not indexed)
    "donnees_personnelles",
    "conditions_generales",
    "mentions_legales",
    "accessibilite",
    "schema_pluriannuel",
    # A placeholder, declined in one variant per ?feature=
    "new_upcoming_feature_notification",
}


@pytest.mark.django_db
def test_every_public_page_is_either_in_sitemap_or_explicitly_excluded():
    accounted_for = (
        set(StaticViewSitemap().items()) | NEVER_LISTED_URL_NAMES | XML_SITEMAP_EXCLUDED_URL_NAMES
    )

    unaccounted = argument_free_url_names() - accounted_for
    assert not unaccounted, (
        f"Page(s) neither in the XML sitemap nor excluded: {sorted(unaccounted)}. "
        "Add them to a sitemap in techpourtoutes.sitemaps, to XML_SITEMAP_EXCLUDED_URL_NAMES, "
        "or to NEVER_LISTED_URL_NAMES if no sitemap should list them (HTMX partial, form "
        "endpoint, funnel step…)."
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
    assert reverse("html_sitemap") in content


@pytest.fixture
def approved_salon(pro):
    from techpourtoutes.models import Event
    from techpourtoutes.tests.models.test_event import build_event

    event = build_event(pro, title="Salon des métiers du numérique", status=Event.Status.APPROVED)
    event.save()
    return event


@pytest.mark.django_db
def test_sitemap_lists_approved_upcoming_events(client, approved_salon):
    content = client.get("/sitemap.xml").content.decode()

    assert reverse("show_event", args=[approved_salon.slug]) in content


@pytest.mark.django_db
def test_sitemap_omits_events_awaiting_validation(client, event):
    content = client.get("/sitemap.xml").content.decode()

    assert reverse("show_event", args=[event.slug]) not in content
