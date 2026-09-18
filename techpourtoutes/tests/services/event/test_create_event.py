import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.forms.event import EventDetailsForm, EventLocationForm, EventSubcategoryForm
from techpourtoutes.models import Event
from techpourtoutes.services.event.create_event import CreateEvent

locmem = override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    NEW_EVENT_RECIPIENTS=["agir@techpourtoutes.io"],
)


def valid_forms(location_overrides=None, **overrides):
    subcategory = EventSubcategoryForm(data={"subcategory": Event.Subcategory.SALON} | overrides)
    details = EventDetailsForm(
        data={
            "organizer": "Numeum",
            "title": "Salon des métiers du numérique",
            "description": "Une journée pour rencontrer des professionnelles.",
            "start_date": "2026-10-01",
            "start_time": "09:00",
            "end_date": "2026-10-02",
            "end_time": "18:00",
        }
    )
    location = EventLocationForm(
        data={
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
        | (location_overrides or {})
    )
    assert subcategory.is_valid() and details.is_valid() and location.is_valid()
    return subcategory, details, location


@pytest.mark.django_db
@locmem
def test_the_event_is_created_awaiting_validation(pro):
    result = CreateEvent(pro=pro, forms=valid_forms())

    assert result.success
    event = Event.objects.get()
    assert event.created_by == pro
    assert event.status == Event.Status.PENDING
    assert event.title == "Salon des métiers du numérique"
    assert event.city == "Amiens"
    assert event.latitude == 49.897443


@pytest.mark.django_db
@locmem
def test_the_free_text_subcategory_is_what_gets_stored(pro):
    forms = valid_forms(
        subcategory=Event.Subcategory.OTHER, subcategory_other="Rencontre d'anciennes"
    )

    CreateEvent(pro=pro, forms=forms)

    assert Event.objects.get().subcategory == "Rencontre d'anciennes"


@pytest.mark.django_db
@locmem
def test_both_the_author_and_the_team_are_notified(pro):
    CreateEvent(pro=pro, forms=valid_forms())

    assert len(mail.outbox) == 2
    to_author = next(msg for msg in mail.outbox if msg.to == [pro.email])
    to_team = next(msg for msg in mail.outbox if msg.to == ["agir@techpourtoutes.io"])
    assert "en cours de validation" in to_author.subject
    assert "à valider" in to_team.subject


@pytest.mark.django_db
@locmem
def test_a_moderators_event_is_published_straight_away(moderator_pro):
    CreateEvent(pro=moderator_pro, forms=valid_forms())

    assert Event.objects.get().status == Event.Status.APPROVED


@pytest.mark.django_db
@locmem
def test_a_superusers_event_is_published_straight_away(pro):
    pro.is_superuser = True
    pro.save()

    CreateEvent(pro=pro, forms=valid_forms())

    assert Event.objects.get().status == Event.Status.APPROVED


@pytest.mark.django_db
@locmem
def test_a_published_event_only_tells_its_author_it_is_online(moderator_pro):
    CreateEvent(pro=moderator_pro, forms=valid_forms())

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [moderator_pro.email]
    assert "en ligne" in mail.outbox[0].subject


@pytest.mark.django_db
@locmem
def test_a_moderators_ungeocoded_event_still_awaits_validation(moderator_pro):
    """The address autocomplete was down: an approved event in presentiel has to be geocoded."""
    forms = valid_forms(
        location_overrides={"longitude": "", "latitude": "", "address_api_down": "1"}
    )

    CreateEvent(pro=moderator_pro, forms=forms)

    assert Event.objects.get().status == Event.Status.PENDING
