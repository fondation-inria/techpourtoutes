from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from techpourtoutes.models import Event

# These tests drive a real browser to cover what the view tests cannot: both behaviours are
# IntersectionObserver / HTMX swaps that only exist once the page runs. The view tests can only
# see that the sentinel and its URL are in the markup, not that scrolling is what triggers them.

EVENTS_PER_PAGE = 12


@pytest.fixture
def fifteen_events(pro):
    today = timezone.localdate()
    for index in range(15):
        start = today + timedelta(days=index + 1)
        Event(
            created_by=pro,
            title=f"Événement numéro {index:02d}",
            organizer="TechPourToutes",
            subcategory=Event.Subcategory.HACKATHON,
            status=Event.Status.APPROVED,
            access_type=Event.AccessType.OPEN,
            location_type=Event.LocationType.ONLINE,
            online_url="https://example.org/evenement",
            start_date=start,
            end_date=start,
            start_time=time(9, 0),
            end_time=time(18, 0),
            price=Decimal("0"),
        ).save()


def test_the_next_events_only_load_once_she_scrolls(page, live_server, fifteen_events):
    """Rooting the sentinel on the grid would make it intersect on load and pull in every page."""
    page.goto(f"{live_server.url}/evenements/")
    cards = page.locator("#events-grid h2")
    expect(cards).to_have_count(EVENTS_PER_PAGE)

    page.mouse.wheel(0, 6000)

    expect(cards).to_have_count(15)


def test_an_anonymous_visitor_is_invited_to_sign_up_before_saving(page, live_server, event):
    event.status = Event.Status.APPROVED
    event.save()
    page.goto(f"{live_server.url}/evenements/")

    page.get_by_label("Enregistrer cet événement").click()

    expect(page.get_by_text("Rejoins le club TechPourToutes")).to_be_visible()
    expect(page.get_by_role("link", name="Créer un compte")).to_be_visible()
