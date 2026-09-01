from decimal import Decimal

from techpourtoutes.forms.event import EventLocationForm
from techpourtoutes.models import Event

GEOCODED = {
    "location_type": Event.LocationType.PHYSICAL,
    "address": "8 Boulevard du Port",
    "postal_code": "80000",
    "city": "Amiens",
    "cog_code": "80021",
    "longitude": "2.29009",
    "latitude": "49.897443",
    "ban_id": "80021_6590_00008",
    "access_type": Event.AccessType.OPEN,
    "price": "0",
}

ONLINE = {
    "location_type": Event.LocationType.ONLINE,
    "online_url": "https://example.org/live",
    "access_type": Event.AccessType.OPEN,
    "price": "0",
}


def test_a_geocoded_physical_event_keeps_its_coordinates():
    form = EventLocationForm(data=GEOCODED)

    assert form.is_valid()
    assert form.cleaned_data["latitude"] == 49.897443
    assert form.cleaned_data["online_url"] == ""


def test_a_physical_event_needs_an_address():
    form = EventLocationForm(data=GEOCODED | {"address": ""})

    assert not form.is_valid()
    assert "address" in form.errors


def test_an_online_event_drops_whatever_address_was_typed_first():
    """She may fill the address, then switch to online: the stale block must not be stored."""
    form = EventLocationForm(data=ONLINE | {"address": "8 Boulevard du Port", "city": "Amiens"})

    assert form.is_valid()
    assert form.cleaned_data["address"] == ""
    assert form.cleaned_data["city"] == ""
    assert form.cleaned_data["latitude"] is None


def test_an_online_event_may_omit_its_connection_link():
    form = EventLocationForm(data=ONLINE | {"online_url": ""})

    assert form.is_valid()


def test_a_manual_address_demands_all_three_fields():
    form = EventLocationForm(
        data={
            "location_type": Event.LocationType.PHYSICAL,
            "address_api_down": "on",
            "address": "Salle des fêtes",
            "access_type": Event.AccessType.OPEN,
            "price": "0",
        }
    )

    assert not form.is_valid()
    assert "postal_code" in form.errors
    assert "city" in form.errors


def test_a_complete_manual_address_is_accepted_without_coordinates():
    form = EventLocationForm(
        data={
            "location_type": Event.LocationType.PHYSICAL,
            "address_api_down": "on",
            "address": "Salle des fêtes",
            "postal_code": "80000",
            "city": "Amiens",
            "access_type": Event.AccessType.OPEN,
            "price": "0",
        }
    )

    assert form.is_valid()
    assert form.cleaned_data["latitude"] is None
    assert form.cleaned_data["ban_id"] == ""


def test_a_access_type_other_than_open_demands_its_link():
    for access_type in (Event.AccessType.REGISTRATION, Event.AccessType.CANDIDACY):
        form = EventLocationForm(data=GEOCODED | {"access_type": access_type})

        assert not form.is_valid()
        assert "registration_url" in form.errors


def test_an_open_event_drops_a_registration_link_typed_first():
    form = EventLocationForm(data=GEOCODED | {"registration_url": "https://example.org/reserver"})

    assert form.is_valid()
    assert form.cleaned_data["registration_url"] == ""


def test_a_paid_event_keeps_its_price():
    form = EventLocationForm(data=GEOCODED | {"price": "12.50"})

    assert form.is_valid()
    assert form.cleaned_data["price"] == Decimal("12.50")


def test_a_negative_price_is_refused():
    form = EventLocationForm(data=GEOCODED | {"price": "-1"})

    assert not form.is_valid()
    assert "price" in form.errors
