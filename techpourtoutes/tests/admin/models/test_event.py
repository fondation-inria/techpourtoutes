from unittest.mock import MagicMock, patch

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from techpourtoutes.models import Event

CHANGELIST = "admin:techpourtoutes_event_changelist"
SEARCH_ADDRESSES = "admin:event_search_addresses"

locmem = override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")

AMIENS_HIT = {
    "label": "8 Boulevard du Port 80000 Amiens",
    "poi_name": "",
    "address": "8 Boulevard du Port",
    "postal_code": "80000",
    "city": "Amiens",
    "cog_code": "80021",
    "longitude": 2.29009,
    "latitude": 49.897443,
    "ban_id": "80021_6590_00008",
}


def _change_url(event):
    return reverse("admin:techpourtoutes_event_change", args=[event.pk])


def _change_form_data(event, **overrides):
    """Everything the change form posts back, so a decision travels with real field values."""
    return {
        "created_by": str(event.created_by.pk),
        "title": event.title,
        "organizer": event.organizer,
        "description": event.description,
        "subcategory_0": event.subcategory,
        "subcategory_1": "",
        "access_type": event.access_type,
        "registration_url": event.registration_url,
        "price": str(event.price),
        "location_type": event.location_type,
        "online_url": event.online_url,
        "start_date": event.start_date.strftime("%Y-%m-%d"),
        "start_time": event.start_time.strftime("%H:%M"),
        "end_date": event.end_date.strftime("%Y-%m-%d"),
        "end_time": event.end_time.strftime("%H:%M"),
        "poi_name": event.poi_name,
        "address": event.address,
        "postal_code": event.postal_code,
        "city": event.city,
        "cog_code": event.cog_code,
        "longitude": "" if event.longitude is None else event.longitude,
        "latitude": "" if event.latitude is None else event.latitude,
        "ban_id": event.ban_id,
        **overrides,
    }


def _decided(event, status):
    """A decided event never needs geocoding: an online event sidesteps that constraint."""
    event.status = status
    event.location_type = Event.LocationType.ONLINE
    event.online_url = "https://example.org/live"
    event.save()
    return event


@pytest.mark.django_db
def test_event_changelist_shows_the_free_text_subcategory(verified_admin_client, event):
    event.subcategory = "Rencontre d'anciennes élèves"
    event.save()

    content = verified_admin_client.get(reverse(CHANGELIST)).content.decode()
    assert "Rencontre d&#x27;anciennes élèves" in content
    assert "Convivial" in content


@pytest.mark.django_db
def test_event_changelist_searches_on_its_creator(verified_admin_client, event):
    """Django validates neither a search_fields path nor a fieldsets omission — tests do."""
    _decided(event, Event.Status.APPROVED)

    response = verified_admin_client.get(reverse(CHANGELIST), {"q": event.created_by.email})

    assert "Salon des métiers du numérique" in response.content.decode()


@pytest.mark.django_db
def test_event_add_form_offers_every_mandatory_field(verified_admin_client):
    response = verified_admin_client.get(reverse("admin:techpourtoutes_event_add"))

    assert "organizer" in response.context["adminform"].form.fields


@pytest.mark.django_db
def test_event_page_offers_its_history(verified_admin_client, event):
    url = reverse("admin:techpourtoutes_event_change", args=[event.pk])
    content = verified_admin_client.get(url).content.decode()
    assert reverse("admin:techpourtoutes_event_history", args=[event.pk]) in content


@pytest.mark.django_db
def test_pending_events_are_listed_above_the_decided_ones(verified_admin_client, event):
    """The bottom list is the real, searchable/filterable changelist — pending events never
    belong there, they still await a decision."""
    decided = _decided(event, Event.Status.APPROVED)
    from techpourtoutes.tests.models.test_event import build_event

    pending = build_event(decided.created_by, title="En attente")
    pending.save()

    content = verified_admin_client.get(reverse(CHANGELIST)).content.decode()

    assert content.index("En attente") < content.index("Salon des métiers du numérique")


@pytest.mark.django_db
def test_no_pending_section_when_nothing_awaits_validation(verified_admin_client, event):
    _decided(event, Event.Status.APPROVED)

    content = verified_admin_client.get(reverse(CHANGELIST)).content.decode()

    assert "à valider" not in content.lower()


@pytest.mark.django_db
def test_status_field_is_hidden_while_pending(verified_admin_client, event):
    """While pending, status only ever moves through Publier/Refuser: showing the raw field
    would invite hand-editing around them."""
    url = reverse("admin:techpourtoutes_event_change", args=[event.pk])
    content = verified_admin_client.get(url).content.decode()
    assert 'name="status"' not in content

    _decided(event, Event.Status.APPROVED)
    content = verified_admin_client.get(url).content.decode()
    assert 'name="status"' in content


@pytest.mark.django_db
def test_moderation_buttons_submit_the_change_form_and_show_only_while_pending(
    verified_admin_client, event
):
    """They save: they belong to the change form, whatever their place on the page."""
    content = verified_admin_client.get(_change_url(event)).content.decode()
    assert 'name="_publish"' in content
    assert 'name="_reject"' in content
    assert content.count('form="event_form"') == 3  # the two buttons and the comment

    _decided(event, Event.Status.APPROVED)
    content = verified_admin_client.get(_change_url(event)).content.decode()
    assert 'name="_publish"' not in content


@pytest.mark.django_db
@locmem
def test_publishing_runs_the_same_checks_as_a_save(verified_admin_client, event):
    """A decision is a save: the geocoding constraint is reported on the form, not after it."""
    data = _change_form_data(event, longitude="", latitude="", _publish="")

    response = verified_admin_client.post(_change_url(event), data)

    assert response.status_code == 200
    content = response.content.decode()
    assert "doit être géocodé" in content
    assert 'name="_publish"' in content  # still offered, next to what it refused
    event.refresh_from_db()
    assert event.status == Event.Status.PENDING
    assert not mail.outbox


@pytest.mark.django_db
@locmem
def test_publishing_reports_a_field_error_instead_of_deciding(verified_admin_client, event):
    data = _change_form_data(event, end_date=event.start_date.strftime("%Y-%m-%d"), _publish="")
    data["end_time"] = "08:00"

    response = verified_admin_client.post(_change_url(event), data)

    assert response.status_code == 200
    assert "doit suivre son début" in response.content.decode()
    event.refresh_from_db()
    assert event.status == Event.Status.PENDING
    assert not mail.outbox


@pytest.mark.django_db
@locmem
def test_publishing_saves_the_edits_it_travels_with(verified_admin_client, event):
    """The geocoding a moderator completed is part of the very submit that publishes."""
    data = _change_form_data(event, address="12 rue Neuve", _publish="", comment="Bravo !")

    response = verified_admin_client.post(_change_url(event), data)

    assert response.status_code == 302
    event.refresh_from_db()
    assert event.status == Event.Status.APPROVED
    assert event.address == "12 rue Neuve"
    assert mail.outbox[0].to == [event.created_by.email]
    assert "Bravo !" in mail.outbox[0].body


@pytest.mark.django_db
@locmem
def test_publishing_a_named_place_without_a_street_address(verified_admin_client, event):
    """A POI hit carries no street: `poi_name` stands in for it, so the form has to offer it."""
    data = _change_form_data(event, address="", poi_name="Station F", _publish="")

    response = verified_admin_client.post(_change_url(event), data)

    assert response.status_code == 302
    event.refresh_from_db()
    assert event.status == Event.Status.APPROVED
    assert event.poi_name == "Station F"


@pytest.mark.django_db
@locmem
def test_rejecting_passes_the_comment_along(verified_admin_client, event):
    data = _change_form_data(event, _reject="", comment="Adresse incomplète.")

    verified_admin_client.post(_change_url(event), data)

    event.refresh_from_db()
    assert event.status == Event.Status.REJECTED
    assert "Adresse incomplète." in mail.outbox[0].body


@pytest.mark.django_db
@locmem
def test_the_comment_is_optional(verified_admin_client, event):
    verified_admin_client.post(_change_url(event), _change_form_data(event, _publish=""))

    event.refresh_from_db()
    assert event.status == Event.Status.APPROVED
    assert len(mail.outbox) == 1


@pytest.mark.django_db
@locmem
def test_a_plain_save_decides_nothing(verified_admin_client, event):
    verified_admin_client.post(_change_url(event), _change_form_data(event, title="Nouveau titre"))

    event.refresh_from_db()
    assert event.status == Event.Status.PENDING
    assert event.title == "Nouveau titre"
    assert not mail.outbox


@pytest.mark.django_db
def test_the_change_form_offers_the_address_search(verified_admin_client, event):
    content = verified_admin_client.get(_change_url(event)).content.decode()

    assert 'id="id_address_search"' in content
    assert reverse(SEARCH_ADDRESSES) in content


@pytest.mark.django_db
def test_the_place_is_written_by_the_search_only(verified_admin_client, event):
    """A hand-named place is exactly what the address search is there to replace — but the
    fields stay form fields, or the constraints hinging on them would go unchecked."""
    form = verified_admin_client.get(_change_url(event)).context["adminform"].form

    place = ("poi_name", "address", "postal_code", "city")
    geocoding = ("cog_code", "longitude", "latitude", "ban_id")
    for name in place + geocoding:
        assert form.fields[name].widget.attrs.get("readonly"), name


@pytest.mark.django_db
def test_the_address_search_answers_the_geocoded_hits_as_json(verified_admin_client):
    with patch(
        "techpourtoutes.admin.models.event.SearchAddresses",
        return_value=MagicMock(addresses=[AMIENS_HIT]),
    ) as mock:
        response = verified_admin_client.get(reverse(SEARCH_ADDRESSES), {"q": "8 bd du port"})

    mock.assert_called_once_with(query="8 bd du port")
    result = response.json()["results"][0]
    assert result["text"] == "8 Boulevard du Port 80000 Amiens"
    assert result["latitude"] == 49.897443
    assert result["address"] == "8 Boulevard du Port"


@pytest.mark.django_db
def test_a_hit_is_identified_by_its_place_not_by_its_rank(verified_admin_client):
    """The dropdown declines to reselect the option it already holds, so a rank would strand
    the moderator on her first pick: every later search offers another place at that rank."""
    poi = {
        "label": "Station F, Paris 13e Arrondissement",
        "poi_name": "Station F",
        "address": "",
        "postal_code": "75013",
        "city": "Paris 13e Arrondissement",
        "cog_code": "75113",
        "longitude": 2.371699,
        "latitude": 48.833436,
        "ban_id": "",
    }

    def search(addresses):
        with patch(
            "techpourtoutes.admin.models.event.SearchAddresses",
            return_value=MagicMock(addresses=addresses),
        ):
            return verified_admin_client.get(reverse(SEARCH_ADDRESSES), {"q": "f"}).json()

    leading = search([poi])["results"][0]
    trailing = search([AMIENS_HIT, poi])["results"][1]

    assert leading["id"] == trailing["id"]
    assert leading["id"] != search([AMIENS_HIT])["results"][0]["id"]


@pytest.mark.django_db
def test_the_address_search_is_staff_only(client):
    response = client.get(reverse(SEARCH_ADDRESSES), {"q": "8 bd du port"})

    assert response.status_code == 302


@pytest.mark.django_db
def test_a_listed_subcategory_offers_its_label_selected(verified_admin_client, event):
    event.subcategory = Event.Subcategory.HACKATHON
    event.save()

    url = reverse("admin:techpourtoutes_event_change", args=[event.pk])
    content = verified_admin_client.get(url).content.decode()

    assert '<option value="hackathon" selected>Hackathon</option>' in content


@pytest.mark.django_db
def test_a_free_text_subcategory_selects_other_and_fills_the_text_input(
    verified_admin_client, event
):
    event.subcategory = "Rencontre d'anciennes élèves"
    event.save()

    url = reverse("admin:techpourtoutes_event_change", args=[event.pk])
    content = verified_admin_client.get(url).content.decode()

    assert '<option value="other" selected>Autre</option>' in content
    assert 'value="Rencontre d&#x27;anciennes élèves"' in content


@pytest.mark.django_db
def test_the_subcategory_field_is_wired_into_a_full_save(verified_admin_client, event):
    """One round trip through the real admin form, proving the custom field is connected —
    its own validation rules are exhaustively covered at the field level."""
    data = _change_form_data(event, subcategory_0="hackathon")

    response = verified_admin_client.post(_change_url(event), data)

    assert response.status_code == 302
    event.refresh_from_db()
    assert event.subcategory == "hackathon"
