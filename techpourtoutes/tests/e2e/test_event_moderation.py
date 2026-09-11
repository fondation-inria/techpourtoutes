import httpx
import pytest
from django.urls import reverse
from playwright.sync_api import expect

from techpourtoutes.models import Event, Pro

from ..models.test_event import build_event

# This test drives a real browser to cover what the admin view tests cannot: the geocoding a
# moderator completes only exists in the page until she decides, written there by select2.

AMIENS = {
    "properties": {
        "_type": "address",
        "id": "80021_6590_00008",
        "label": "8 Boulevard du Port 80000 Amiens",
        "name": "8 Boulevard du Port",
        "postcode": "80000",
        "city": "Amiens",
        "citycode": "80021",
    },
    "geometry": {"coordinates": [2.290084, 49.897442]},
}
AMIENS_LABEL = "8 Boulevard du Port 80000 Amiens"

STATION_F = {
    "properties": {
        "_type": "poi",
        "toponym": "Station F",
        "postcode": ["75013"],
        "city": ["Paris 13e Arrondissement", "Paris"],
        "citycode": ["75113", "75056"],
    },
    "geometry": {"coordinates": [2.371699, 48.833436]},
}
STATION_F_LABEL = "Station F, Paris 13e Arrondissement"


@pytest.fixture
def geocoding(httpx_mock):
    """One hit per query, whichever index it belongs to: each search then offers its place at
    the same rank as the last, which is where a dropdown gets its identity from."""

    def respond(request):
        params = request.url.params
        hit = STATION_F if "station" in params["q"] else AMIENS
        wanted = params["index"] == hit["properties"]["_type"]
        return httpx.Response(200, json={"features": [hit] if wanted else []})

    httpx_mock.add_callback(respond, is_reusable=True)


@pytest.fixture
def ungeocoded_event(db, settings):
    """What the funnel leaves behind when the address API was down: a place named by hand,
    with no coordinates — the one thing a moderator cannot publish as is."""
    settings.DISABLE_ADMIN_2FA = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    moderator = Pro(
        username="admin@example.com",
        civility=Pro.Civility.MADAME,
        first_name="Alice",
        last_name="Martin",
        email="admin@example.com",
        professional_situation=Pro.ProfessionalSituation.WORKING,
        is_staff=True,
        is_superuser=True,
    )
    moderator.save()
    moderator.set_password("moderation-pass")
    moderator.save(update_fields=["password"])
    event = build_event(
        moderator,
        location_type=Event.LocationType.PHYSICAL,
        address="8 boulevard du port",
        city="Amiens",
    )
    event.save()
    return event


@pytest.fixture
def moderation(live_server, page, ungeocoded_event):
    """Both decisions confirm before submitting: without this the click is a no-op."""
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(live_server.url + reverse("admin:login"))
    page.fill('input[name="username"]', "admin@example.com")
    page.fill('input[name="password"]', "moderation-pass")
    page.get_by_role("button", name="Connexion").click()
    page.goto(
        live_server.url + reverse("admin:techpourtoutes_event_change", args=[ungeocoded_event.pk])
    )
    return page


def pick(page, query, option):
    page.locator(".select2-selection").click()
    page.locator("input.select2-search__field").fill(query)
    page.get_by_role("option", name=option).click()


def test_an_ungeocoded_event_is_geocoded_then_published(moderation, ungeocoded_event, geocoding):
    moderation.get_by_role("button", name="Publier").click()
    expect(moderation.get_by_text("doit être géocodé")).to_be_visible()

    pick(moderation, "8 boulevard du port", AMIENS_LABEL)

    expect(moderation.locator("#id_latitude")).to_have_value("49.897442")
    moderation.get_by_role("button", name="Publier").click()

    expect(moderation.get_by_text("a été publié")).to_be_visible()
    ungeocoded_event.refresh_from_db()
    assert ungeocoded_event.status == Event.Status.APPROVED
    assert ungeocoded_event.latitude == 49.897442
    assert ungeocoded_event.ban_id == "80021_6590_00008"
