from decimal import Decimal

import pytest

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
    "pricing": "free",
}

VENUE = {
    "location_type": Event.LocationType.PHYSICAL,
    "poi_name": "Station F",
    "city": "Paris 13e Arrondissement",
    "cog_code": "75113",
    "longitude": "2.371699",
    "latitude": "48.833436",
    "access_type": Event.AccessType.OPEN,
    "pricing": "free",
}

ONLINE = {
    "location_type": Event.LocationType.ONLINE,
    "online_url": "https://example.org/live",
    "access_type": Event.AccessType.OPEN,
    "pricing": "free",
}


def test_a_geocoded_physical_event_keeps_its_coordinates():
    form = EventLocationForm(data=GEOCODED)

    assert form.is_valid()
    assert form.cleaned_data["latitude"] == 49.897443
    assert form.cleaned_data["online_url"] == ""


def test_a_physical_event_needs_an_address_or_a_venue():
    form = EventLocationForm(data=GEOCODED | {"address": ""})

    assert not form.is_valid()
    assert "address" in form.errors


def test_a_venue_stands_in_for_the_street_address():
    """A POI has no street: its name and its commune are all the API gives."""
    form = EventLocationForm(data=VENUE)

    assert form.is_valid()
    assert form.cleaned_data["poi_name"] == "Station F"
    assert form.cleaned_data["address"] == ""
    assert form.cleaned_data["latitude"] == 48.833436


def test_an_online_event_drops_whatever_address_was_typed_first():
    """She may fill the address, then switch to online: the stale block must not be stored."""
    form = EventLocationForm(data=ONLINE | {"address": "8 Boulevard du Port", "city": "Amiens"})

    assert form.is_valid()
    assert form.cleaned_data["address"] == ""
    assert form.cleaned_data["city"] == ""
    assert form.cleaned_data["latitude"] is None


def test_an_online_event_drops_a_venue_picked_first():
    form = EventLocationForm(data=ONLINE | {"poi_name": "Station F"})

    assert form.is_valid()
    assert form.cleaned_data["poi_name"] == ""


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
            "pricing": "free",
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
            "pricing": "free",
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


def test_a_malformed_connection_link_names_the_expected_format():
    """The input is a plain text field, so the browser lets it through: the message telling her
    what a link looks like has to come from here."""
    form = EventLocationForm(data=ONLINE | {"online_url": "visio de la salle"})

    assert not form.is_valid()
    assert "www.techpourtoutes.io" in form.errors["online_url"][0]


def test_a_malformed_registration_link_names_the_expected_format():
    """A link that failed to parse leaves the field empty, which used to read as a missing one:
    she was told to fill in what she had just filled in."""
    form = EventLocationForm(
        data=GEOCODED
        | {"access_type": Event.AccessType.REGISTRATION, "registration_url": "sur place"}
    )

    assert not form.is_valid()
    assert len(form.errors["registration_url"]) == 1
    assert "www.techpourtoutes.io" in form.errors["registration_url"][0]


def test_a_free_event_is_stored_at_zero():
    """`pricing` is the answer she gives; the price column is what it amounts to."""
    form = EventLocationForm(data=GEOCODED)

    assert form.is_valid()
    assert form.cleaned_data["price"] == 0


def test_a_free_event_drops_a_price_typed_first():
    form = EventLocationForm(data=GEOCODED | {"price": "12,50"})

    assert form.is_valid()
    assert form.cleaned_data["price"] == 0


def test_a_paid_event_demands_its_price():
    form = EventLocationForm(data=GEOCODED | {"pricing": "paid"})

    assert not form.is_valid()
    assert "price" in form.errors


def test_a_paid_event_keeps_its_price():
    """The comma is the separator she is offered as an example, and the dot the one a keypad
    hands her: both mean twelve fifty."""
    for typed in ("12,50", "12.50"):
        form = EventLocationForm(data=GEOCODED | {"pricing": "paid", "price": typed})

        assert form.is_valid()
        assert form.cleaned_data["price"] == Decimal("12.50")


def test_a_price_typed_in_words_names_the_expected_format():
    form = EventLocationForm(data=GEOCODED | {"pricing": "paid", "price": "douze euros"})

    assert not form.is_valid()
    assert "12,50" in form.errors["price"][0]


def test_a_negative_price_is_refused():
    form = EventLocationForm(data=GEOCODED | {"pricing": "paid", "price": "-1"})

    assert not form.is_valid()
    assert "price" in form.errors


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_hands_back_a_geocoded_address_this_form_parses(event):
    answers = EventLocationForm(event=event).initial

    assert all(isinstance(value, str) for value in answers.values())
    form = EventLocationForm(data=answers)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["address"] == event.address
    assert form.cleaned_data["latitude"] == event.latitude
    assert form.cleaned_data["price"] == event.price


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_reads_the_pricing_branch_back_off_the_price(pro):
    """`pricing` is the question she answered, not a column the event carries."""
    from ...models.test_event import build_event

    paid = build_event(pro, price=Decimal("12.50"))
    paid.save()

    answers = EventLocationForm(event=paid).initial

    assert answers["pricing"] == "paid"
    form = EventLocationForm(data=answers)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["price"] == Decimal("12.50")


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_leaves_an_online_event_without_coordinates(pro):
    from ...models.test_event import build_event

    online = build_event(pro, location_type=Event.LocationType.ONLINE, city="")
    online.save()

    answers = EventLocationForm(event=online).initial

    assert answers["longitude"] == ""
    assert answers["latitude"] == ""
    assert EventLocationForm(data=answers).is_valid()


def test_event_fields_drops_the_answers_the_event_does_not_carry():
    form = EventLocationForm(data=GEOCODED)

    assert form.is_valid()
    assert "pricing" not in form.event_fields
    assert "address_api_down" not in form.event_fields
    assert form.event_fields["address"] == "8 Boulevard du Port"
