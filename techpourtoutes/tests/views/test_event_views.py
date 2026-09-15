from datetime import timedelta

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse, reverse_lazy
from django.utils import timezone

from techpourtoutes.models import Event

NEW_EVENT_URL = reverse_lazy("new_event")
CREATE_URL = reverse_lazy("create_event")
UPDATE_URL = reverse_lazy("update_event")

locmem = override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    NEW_EVENT_RECIPIENTS=["agir@techpourtoutes.io"],
)

SUBCATEGORY = {"subcategory": Event.Subcategory.SALON}

DETAILS = {
    "organizer": "Numeum",
    "title": "Salon des métiers du numérique",
    "description": "Une journée pour rencontrer des professionnelles.",
    "start_date": "2026-10-01",
    "start_time": "09:00",
    "end_date": "2026-10-02",
    "end_time": "18:00",
}

LOCATION = {
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


# The client carries every answer collected so far in hidden inputs, so a step is always
# posted with the whole payload rather than by chaining requests.
def answers(**overrides):
    return SUBCATEGORY | DETAILS | LOCATION | overrides


@pytest.mark.django_db
def test_the_funnel_is_reserved_to_pros(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(NEW_EVENT_URL, follow=True)

    assert response.redirect_chain[-1][0] == reverse("show_account")
    assert any("réservée aux professionnelles" in str(m) for m in response.context["messages"])


@pytest.mark.django_db
def test_an_anonymous_visitor_is_sent_to_the_login_page(client):
    response = client.get(NEW_EVENT_URL)

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_the_first_screen_asks_for_the_subcategory(client, pro):
    client.force_login(pro)

    content = client.get(NEW_EVENT_URL).content.decode()

    assert 'name="action" value="subcategory"' in content
    assert "voulez-vous proposer" in content


@pytest.mark.django_db
def test_a_valid_category_leads_to_the_details_screen(client, pro):
    client.force_login(pro)

    content = client.post(CREATE_URL, {"action": "subcategory", **SUBCATEGORY}).content.decode()

    assert 'name="action" value="details"' in content
    assert "Nom de l&#x27;organisateur" in content


@pytest.mark.django_db
def test_a_missing_category_stays_on_the_first_screen(client, pro):
    client.force_login(pro)

    content = client.post(CREATE_URL, {"action": "subcategory"}).content.decode()

    assert 'name="action" value="subcategory"' in content


@pytest.mark.django_db
def test_a_valid_details_screen_leads_to_the_location_screen(client, pro):
    client.force_login(pro)

    content = client.post(
        CREATE_URL, {"action": "details", **SUBCATEGORY, **DETAILS}
    ).content.decode()

    assert 'name="action" value="location"' in content
    assert "Où se déroule" in content


@pytest.mark.django_db
def test_the_price_question_is_asked_by_the_shared_segmented_component(client, pro):
    """Gratuit/Payant is a field of its own, so it renders as radios like the two questions
    above it rather than as buttons wired to the price input."""
    client.force_login(pro)

    content = client.post(
        CREATE_URL, {"action": "details", **SUBCATEGORY, **DETAILS}
    ).content.decode()

    assert "est-il gratuit" in content
    assert 'name="pricing"' in content
    assert 'value="paid"' in content


@pytest.mark.django_db
def test_the_details_screen_carries_the_category_forward(client, pro):
    client.force_login(pro)

    content = client.post(CREATE_URL, {"action": "subcategory", **SUBCATEGORY}).content.decode()

    assert 'name="subcategory" value="salon"' in content


@pytest.mark.django_db
def test_going_back_re_renders_the_previous_screen_prefilled(client, pro):
    client.force_login(pro)

    content = client.post(
        CREATE_URL, {"action": "back", "to": "location", **SUBCATEGORY, **DETAILS}
    ).content.decode()

    assert 'name="action" value="details"' in content
    assert "Salon des métiers du numérique" in content
    # The step's own fields come back as visible inputs, never also as hidden carried ones.
    assert 'type="hidden" name="title"' not in content


@pytest.mark.django_db
def test_an_unknown_action_falls_back_to_the_first_screen(client, pro):
    """A forged `action` must not skip a step: it is treated as the first one."""
    client.force_login(pro)

    content = client.post(CREATE_URL, {"action": "n-importe-quoi", **answers()}).content.decode()

    assert 'name="action" value="details"' in content


@pytest.mark.django_db
def test_going_back_from_an_unknown_step_lands_on_the_first_screen(client, pro):
    client.force_login(pro)

    content = client.post(
        CREATE_URL, {"action": "back", "to": "n-importe-quoi", **SUBCATEGORY}
    ).content.decode()

    assert 'name="action" value="subcategory"' in content


@pytest.mark.django_db
@locmem
def test_publishing_creates_a_pending_event_and_sends_both_mails(client, pro):
    client.force_login(pro)

    content = client.post(CREATE_URL, {"action": "location", **answers()}).content.decode()

    event = Event.objects.get()
    assert event.created_by == pro
    assert event.status == Event.Status.PENDING
    assert event.title == "Salon des métiers du numérique"
    assert "en cours de validation" in content
    assert {tuple(msg.to) for msg in mail.outbox} == {
        (pro.email,),
        ("agir@techpourtoutes.io",),
    }


@pytest.mark.django_db
@locmem
def test_publishing_re_validates_every_earlier_step(client, pro):
    """A forged payload must not slip past: the last screen replays all three validators."""
    client.force_login(pro)

    content = client.post(
        CREATE_URL, {"action": "location", **answers(end_date="2026-09-01")}
    ).content.decode()

    assert not Event.objects.exists()
    assert not mail.outbox
    assert 'name="action" value="details"' in content


@pytest.mark.django_db
@locmem
def test_publishing_an_online_event_stores_no_address(client, pro):
    client.force_login(pro)

    client.post(
        CREATE_URL,
        {
            "action": "location",
            **answers(
                location_type=Event.LocationType.ONLINE, online_url="https://example.org/live"
            ),
        },
    )

    event = Event.objects.get()
    assert event.online_url == "https://example.org/live"
    assert event.address == ""
    assert event.latitude is None


# ------------------- the pro's own listing -------------------

MY_EVENTS_URL = reverse_lazy("index_pro_events")


def approved_event(pro, **overrides):
    from ..models.test_event import build_event

    return build_event(pro, **{"status": Event.Status.APPROVED, **overrides})


@pytest.mark.django_db
def test_index_pro_events_is_reserved_to_pros(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(MY_EVENTS_URL, follow=True)

    assert response.redirect_chain[-1][0] == reverse("show_account")


@pytest.mark.django_db
def test_index_pro_events_lists_the_upcoming_events_from_the_nearest_to_the_furthest(client, pro):
    today = timezone.localdate()
    for title, days in [("Dans deux mois", 60), ("Dans cinq jours", 5)]:
        day = today + timedelta(days=days)
        approved_event(pro, title=title, start_date=day, end_date=day).save()
    client.force_login(pro)

    content = client.get(MY_EVENTS_URL).content.decode()

    assert content.index("Dans cinq jours") < content.index("Dans deux mois")


@pytest.mark.django_db
def test_index_pro_events_cards_link_to_the_event_page(client, pro):
    salon = approved_event(pro, title="Salon des métiers du numérique")
    salon.save()
    client.force_login(pro)

    content = client.get(MY_EVENTS_URL).content.decode()

    assert reverse("show_event", args=[salon.slug]) in content


@pytest.mark.django_db
def test_index_pro_events_ignores_the_events_of_another_pro(client, pro, valid_pro_model_data):
    from techpourtoutes.models import Pro

    other = Pro(**{**valid_pro_model_data, "username": "bea@example.com"})
    other.save()
    approved_event(other, title="Forum d'une autre").save()
    client.force_login(pro)

    assert "une autre" not in client.get(MY_EVENTS_URL).content.decode()


@pytest.mark.django_db
def test_index_pro_events_lists_the_events_awaiting_validation(client, pro, event):
    """The `event` fixture is PENDING: its card sits under its own heading, and opens like
    any other — only its author can follow the link."""
    client.force_login(pro)

    content = client.get(MY_EVENTS_URL).content.decode()

    assert "Événements en attente de validation" in content
    assert event.title in content
    assert reverse("show_event", args=[event.slug]) in content


@pytest.mark.django_db
def test_index_pro_events_hides_the_pending_section_when_nothing_waits(client, pro):
    approved_event(pro).save()
    client.force_login(pro)

    assert "en attente de validation" not in client.get(MY_EVENTS_URL).content.decode()


@pytest.mark.django_db
def test_index_pro_events_lists_the_past_events_under_their_own_heading(client, pro):
    today = timezone.localdate()
    approved_event(
        pro,
        title="Hackathon de l'an dernier",
        start_date=today - timedelta(days=3),
        end_date=today - timedelta(days=1),
    ).save()
    client.force_login(pro)

    content = client.get(MY_EVENTS_URL).content.decode()

    assert "Événements passés" in content
    assert "an dernier" in content


@pytest.mark.django_db
def test_index_pro_events_hides_the_past_section_when_there_is_none(client, pro):
    approved_event(pro).save()
    client.force_login(pro)

    assert "Événements passés" not in client.get(MY_EVENTS_URL).content.decode()


@pytest.mark.django_db
def test_index_pro_events_illustrates_the_empty_state(client, pro):
    client.force_login(pro)

    content = client.get(MY_EVENTS_URL).content.decode()

    assert "Vous n'avez aucun événement." in content
    assert "empty-event-bg" in content


# ------------------- editing an event -------------------


def edit_url(event):
    return reverse("edit_event", args=[event.pk])


@pytest.mark.django_db
def test_edit_event_opens_the_funnel_on_the_answers_the_event_already_holds(client, pro, event):
    client.force_login(pro)

    content = client.get(edit_url(event)).content.decode()

    assert f'name="event" value="{event.pk}"' in content
    assert f'name="title" value="{event.title}"' in content
    assert f'value="{event.subcategory}" selected' in content or event.subcategory in content


@pytest.mark.django_db
def test_edit_event_carries_the_dates_in_a_format_the_form_parses(client, pro, event):
    client.force_login(pro)

    content = client.get(edit_url(event)).content.decode()

    assert f'name="start_date" value="{event.start_date.isoformat()}"' in content
    assert f'name="start_time" value="{event.start_time.strftime("%H:%M")}"' in content


@pytest.mark.django_db
def test_edit_event_is_reserved_to_the_pro_who_submitted_it(client, event, valid_pro_model_data):
    from techpourtoutes.models import Pro

    other = Pro(**{**valid_pro_model_data, "username": "bea@example.com"})
    other.save()
    client.force_login(other)

    assert client.get(edit_url(event)).status_code == 404


@pytest.mark.django_db
@locmem
def test_editing_an_event_awaiting_validation_saves_it_without_asking(client, pro, event):
    client.force_login(pro)

    response = client.post(
        UPDATE_URL, {"action": "location", "event": str(event.pk), **answers(title="Nouveau nom")}
    )

    event.refresh_from_db()
    assert event.title == "Nouveau nom"
    assert response["HX-Redirect"] == reverse("show_event", args=[event.slug])
    assert [msg.to for msg in mail.outbox] == [["agir@techpourtoutes.io"]]


@pytest.mark.django_db
@locmem
def test_editing_an_approved_event_asks_before_publishing(client, pro, event):
    event.status = Event.Status.APPROVED
    event.save()
    client.force_login(pro)

    content = client.post(
        UPDATE_URL, {"action": "location", "event": str(event.pk), **answers(title="Nouveau nom")}
    ).content.decode()

    assert "Voulez-vous modifier votre événement" in content
    assert "Publier les modifications" in content
    assert "Quitter" in content
    event.refresh_from_db()
    assert event.title != "Nouveau nom"
    assert not mail.outbox


@pytest.mark.django_db
@locmem
def test_confirming_the_edit_of_an_approved_event_publishes_it(client, pro, event, beneficiary):
    from techpourtoutes.models import SavedEvent

    event.status = Event.Status.APPROVED
    event.save()
    SavedEvent.objects.create(event=event, beneficiary=beneficiary)
    client.force_login(pro)

    response = client.post(
        UPDATE_URL,
        {
            "action": "location",
            "event": str(event.pk),
            "confirmed": "1",
            **answers(title="Nouveau nom"),
        },
    )

    event.refresh_from_db()
    assert event.title == "Nouveau nom"
    assert response["HX-Redirect"] == reverse("show_event", args=[event.slug])
    assert {tuple(msg.to) for msg in mail.outbox} == {
        ("agir@techpourtoutes.io",),
        (pro.email,),
        (beneficiary.email,),
    }


@pytest.mark.django_db
@locmem
def test_editing_an_event_that_belongs_to_another_pro_is_a_404(
    client, pro, event, valid_pro_model_data
):
    from techpourtoutes.models import Pro

    other = Pro(**{**valid_pro_model_data, "username": "bea@example.com"})
    other.save()
    client.force_login(other)

    response = client.post(
        UPDATE_URL, {"action": "location", "event": str(event.pk), **answers(title="Nouveau nom")}
    )

    assert response.status_code == 404
    event.refresh_from_db()
    assert event.title != "Nouveau nom"


@pytest.mark.django_db
@locmem
def test_a_forged_event_id_creates_nothing(client, pro):
    client.force_login(pro)

    response = client.post(UPDATE_URL, {"action": "location", "event": "pas-un-uuid", **answers()})

    assert response.status_code == 404
    assert not Event.objects.exists()


@pytest.mark.django_db
def test_the_event_being_edited_travels_from_one_step_to_the_next(client, pro, event):
    client.force_login(pro)

    content = client.post(
        UPDATE_URL, {"action": "subcategory", "event": str(event.pk), **SUBCATEGORY}
    ).content.decode()

    assert f'name="event" value="{event.pk}"' in content


@pytest.mark.django_db
def test_edit_event_says_it_is_an_edit_rather_than_a_new_proposal(client, pro, event):
    client.force_login(pro)

    content = client.get(edit_url(event)).content.decode()

    assert "Modifier un événement" in content
    assert "Proposer un événement" not in content
    assert "quitter la modification" in content
    assert "création" not in content


@pytest.mark.django_db
def test_the_funnel_still_says_it_proposes_an_event_when_nothing_is_being_edited(client, pro):
    client.force_login(pro)

    content = client.get(NEW_EVENT_URL).content.decode()

    assert "Proposer un événement" in content
    assert "Modifier un événement" not in content


@pytest.mark.django_db
def test_a_later_step_of_an_edit_keeps_saying_it_is_an_edit(client, pro, event):
    client.force_login(pro)

    content = client.post(
        UPDATE_URL, {"action": "subcategory", "event": str(event.pk), **SUBCATEGORY}
    ).content.decode()

    assert "Modifier un événement" in content


@pytest.mark.django_db
def test_create_event_rejects_a_get(client, pro):
    """The funnel's screens are posted: the first one has a route of its own."""
    client.force_login(pro)

    assert client.get(CREATE_URL).status_code == 405


@pytest.mark.django_db
def test_update_event_rejects_a_get(client, pro):
    client.force_login(pro)

    assert client.get(UPDATE_URL).status_code == 405


@pytest.mark.django_db
def test_update_event_without_an_event_to_edit_is_a_404(client, pro):
    client.force_login(pro)

    assert client.post(UPDATE_URL, {"action": "location", **answers()}).status_code == 404
