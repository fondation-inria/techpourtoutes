from unittest.mock import MagicMock, patch

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from techpourtoutes.models import Event

CHANGELIST = "admin:techpourtoutes_event_changelist"


def _moderate_url(event):
    return reverse("admin:event_moderate", args=[event.pk])


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
def test_moderation_buttons_shown_only_while_pending(verified_admin_client, event):
    url = reverse("admin:techpourtoutes_event_change", args=[event.pk])
    content = verified_admin_client.get(url).content.decode()
    assert _moderate_url(event) in content
    assert "Publier" in content
    assert "Refuser" in content

    _decided(event, Event.Status.APPROVED)
    content = verified_admin_client.get(url).content.decode()
    assert _moderate_url(event) not in content


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_publishing_calls_moderate_event_and_redirects(verified_admin_client, event):
    instance = MagicMock(success=True, failure=False, errors=[])
    with patch("techpourtoutes.admin.models.event.ModerateEvent", return_value=instance) as mock:
        response = verified_admin_client.post(
            _moderate_url(event), {"decision": Event.Status.APPROVED, "comment": "Bravo !"}
        )

    mock.assert_called_once_with(event=event, status=Event.Status.APPROVED, comment="Bravo !")
    assert response.status_code == 302
    assert response["Location"] == reverse("admin:techpourtoutes_event_change", args=[event.pk])
    assert not mail.outbox  # the mailer lives in ModerateEvent, mocked away here


@pytest.mark.django_db
def test_rejecting_passes_the_comment_along(verified_admin_client, event):
    instance = MagicMock(success=True, failure=False, errors=[])
    with patch("techpourtoutes.admin.models.event.ModerateEvent", return_value=instance) as mock:
        verified_admin_client.post(
            _moderate_url(event),
            {"decision": Event.Status.REJECTED, "comment": "Adresse incomplète."},
        )

    mock.assert_called_once_with(
        event=event, status=Event.Status.REJECTED, comment="Adresse incomplète."
    )


@pytest.mark.django_db
def test_the_comment_is_optional(verified_admin_client, event):
    instance = MagicMock(success=True, failure=False, errors=[])
    with patch("techpourtoutes.admin.models.event.ModerateEvent", return_value=instance) as mock:
        verified_admin_client.post(_moderate_url(event), {"decision": Event.Status.APPROVED})

    mock.assert_called_once_with(event=event, status=Event.Status.APPROVED, comment="")


@pytest.mark.django_db
def test_moderation_failure_is_shown_and_the_page_reloads(verified_admin_client, event):
    instance = MagicMock(success=False, failure=True, errors=["Événement non géocodé."])
    with patch("techpourtoutes.admin.models.event.ModerateEvent", return_value=instance):
        response = verified_admin_client.post(
            _moderate_url(event), {"decision": Event.Status.APPROVED}, follow=True
        )

    assert "Événement non géocodé." in response.content.decode()


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
    url = reverse("admin:techpourtoutes_event_change", args=[event.pk])
    data = {
        "created_by": str(event.created_by.pk),
        "title": event.title,
        "organizer": event.organizer,
        "description": event.description,
        "subcategory_0": "hackathon",
        "subcategory_1": "",
        "status": event.status,
        "access_type": event.access_type,
        "registration_url": event.registration_url,
        "price": str(event.price),
        "location_type": event.location_type,
        "online_url": event.online_url,
        "start_date": event.start_date.strftime("%Y-%m-%d"),
        "start_time": event.start_time.strftime("%H:%M"),
        "end_date": event.end_date.strftime("%Y-%m-%d"),
        "end_time": event.end_time.strftime("%H:%M"),
        "address": event.address,
        "postal_code": event.postal_code,
        "city": event.city,
        "cog_code": event.cog_code,
        "longitude": event.longitude,
        "latitude": event.latitude,
        "ban_id": event.ban_id,
    }

    response = verified_admin_client.post(url, data)

    assert response.status_code == 302
    event.refresh_from_db()
    assert event.subcategory == "hackathon"
