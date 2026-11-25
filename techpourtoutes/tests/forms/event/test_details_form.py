from datetime import datetime, timedelta

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.utils import timezone

from techpourtoutes.forms.event import EventDetailsForm
from techpourtoutes.models import Event
from techpourtoutes.utils.time_zones import TimeZone

from ...models.test_event import build_event

START = timezone.localdate() + timedelta(days=30)

VALID = {
    "organizer": "Numeum",
    "title": "Salon des métiers du numérique",
    "description": "Une journée pour rencontrer des professionnelles de la tech.",
    "start_date": START.isoformat(),
    "start_time": "09:00",
    "end_date": (START + timedelta(days=1)).isoformat(),
    "end_time": "18:00",
}


@pytest.fixture(autouse=True)
def at_three_pm_on_october_first(monkeypatch):
    now = timezone.make_aware(datetime(2026, 10, 1, 15, 0))
    monkeypatch.setattr(timezone, "now", lambda: now)


def test_a_complete_form_is_valid():
    assert EventDetailsForm(data=VALID).is_valid()


def test_every_field_is_required():
    form = EventDetailsForm(data={})

    assert not form.is_valid()
    assert set(form.errors) == set(VALID)


def test_an_end_date_before_the_start_date_is_refused():
    form = EventDetailsForm(data=VALID | {"end_date": (START - timedelta(days=1)).isoformat()})

    assert not form.is_valid()
    assert "end_date" in form.errors


def test_an_end_time_before_the_start_time_on_a_single_day_is_refused():
    form = EventDetailsForm(
        data=VALID | {"end_date": VALID["start_date"], "start_time": "18:00", "end_time": "09:00"}
    )

    assert not form.is_valid()
    assert "end_time" in form.errors


def test_a_single_day_event_may_start_and_end_at_the_same_time():
    form = EventDetailsForm(
        data=VALID | {"end_date": VALID["start_date"], "start_time": "09:00", "end_time": "09:00"}
    )

    assert form.is_valid()


def test_an_event_already_over_is_refused():
    form = EventDetailsForm(data=VALID | {"start_date": "2020-01-01", "end_date": "2020-01-02"})

    assert not form.is_valid()
    assert "end_date" in form.errors


def today_ending_at(end_time):
    today = timezone.localdate().isoformat()
    return VALID | {
        "start_date": today,
        "end_date": today,
        "start_time": "00:00",
        "end_time": end_time,
    }


def test_an_event_over_in_every_time_zone_is_refused():
    """At 15:00 in Paris, it is 03:00 in Tahiti, where the clock is furthest behind."""
    form = EventDetailsForm(data=today_ending_at("02:59"))

    assert not form.is_valid()
    assert "end_time" in form.errors


def test_an_event_over_on_paris_time_but_not_further_west_is_accepted():
    """Left unticked, the zone is not known yet: a physical event takes the one of its postal
    code, asked on the next screen."""
    form = EventDetailsForm(data=today_ending_at("14:59"))

    assert form.is_valid()


def test_an_event_ended_yesterday_on_paris_time_but_not_in_tahiti_is_accepted(monkeypatch):
    """At 09:00 in Paris on October 1st, it is still 21:00 on September 30th in Tahiti."""
    now = timezone.make_aware(datetime(2026, 10, 1, 9, 0))
    monkeypatch.setattr(timezone, "now", lambda: now)

    form = EventDetailsForm(
        data=VALID | {"start_date": "2026-09-30", "end_date": "2026-09-30", "end_time": "22:00"}
    )

    assert form.is_valid()


def test_an_event_ending_later_today_is_accepted():
    form = EventDetailsForm(data=today_ending_at("15:00"))

    assert form.is_valid()


def in_time_zone(time_zone):
    return {"choose_time_zone": "on", "time_zone": time_zone}


def test_an_event_over_in_the_time_zone_she_chose_is_refused():
    """At 15:00 in Paris on October 1st, it is already 17:00 in La Réunion."""
    form = EventDetailsForm(data=today_ending_at("16:59") | in_time_zone(TimeZone.REUNION))

    assert not form.is_valid()
    assert "end_time" in form.errors


def test_an_event_still_running_in_the_time_zone_she_chose_is_accepted():
    """At 15:00 in Paris on October 1st, it is only 09:00 in Martinique."""
    form = EventDetailsForm(data=today_ending_at("09:00") | in_time_zone(TimeZone.MARTINIQUE))

    assert form.is_valid()


def test_an_event_is_on_paris_time_unless_she_chooses_otherwise():
    """A zone left selected after she unticked the box is not the one she wants."""
    form = EventDetailsForm(data=VALID | {"time_zone": TimeZone.REUNION})

    assert form.is_valid()
    assert form.cleaned_data["time_zone"] == TimeZone.PARIS


def test_an_event_takes_the_time_zone_she_chose():
    form = EventDetailsForm(data=VALID | in_time_zone(TimeZone.REUNION))

    assert form.is_valid()
    assert form.cleaned_data["time_zone"] == TimeZone.REUNION


def test_choosing_a_time_zone_demands_one():
    form = EventDetailsForm(data=VALID | {"choose_time_zone": "on"})

    assert not form.is_valid()
    assert "time_zone" in form.errors


def test_the_time_zones_offered_leave_paris_out():
    """Paris, or the zone of her address, is what she gets by leaving the box unticked."""
    offered = [value for value, _ in EventDetailsForm().fields["time_zone"].choices]

    assert TimeZone.PARIS not in offered
    assert TimeZone.REUNION in offered


def test_an_event_started_yesterday_and_ending_tomorrow_is_accepted():
    today = timezone.localdate()
    form = EventDetailsForm(
        data=VALID
        | {
            "start_date": (today - timedelta(days=1)).isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
        }
    )

    assert form.is_valid()


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_hands_back_dates_and_times_this_form_parses(event):
    """They travel through a hidden input: anything but a string would come back localised."""
    event.description = "Une journée pour rencontrer des professionnelles."
    event.save()

    answers = EventDetailsForm(event=event).initial

    assert all(isinstance(value, str) for value in answers.values())
    form = EventDetailsForm(data=answers)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["start_date"] == event.start_date
    assert form.cleaned_data["start_time"] == event.start_time
    assert form.cleaned_data["title"] == event.title


def test_event_fields_carries_every_answer_of_the_screen_but_the_box():
    """Whether she ticked it is read back off the time zone."""
    form = EventDetailsForm(data=VALID)

    assert form.is_valid()
    assert form.event_fields["title"] == VALID["title"]
    assert set(form.event_fields) == set(EventDetailsForm.base_fields) - {"choose_time_zone"}


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_hands_back_the_time_zone_she_chose(pro):
    online = build_event(pro, description="Un webinaire.", time_zone=TimeZone.MARTINIQUE)
    online.save()

    answers = EventDetailsForm(event=online).initial

    assert answers["choose_time_zone"] == "on"
    form = EventDetailsForm(data=answers)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["time_zone"] == TimeZone.MARTINIQUE


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_on_paris_time_leaves_the_box_unticked(pro):
    online = build_event(pro)
    online.save()

    answers = EventDetailsForm(event=online).initial

    assert answers["choose_time_zone"] == ""
    assert answers["time_zone"] == ""


def overseas_event(pro, **overrides):
    return build_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        address="1 rue de Paris",
        postal_code="97400",
        city="Saint-Denis",
        **overrides,
    )


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_on_the_clock_of_its_place_leaves_the_box_unticked(
    pro,
):
    """Her address gave the zone: she never chose it."""
    event = overseas_event(pro)
    event.save()

    answers = EventDetailsForm(event=event).initial

    assert answers["choose_time_zone"] == ""


@pytest.mark.django_db
def test_the_form_prefilled_from_a_physical_event_hands_back_a_time_zone_she_chose(pro):
    event = overseas_event(pro, time_zone=TimeZone.MAYOTTE)
    event.save()

    answers = EventDetailsForm(event=event).initial

    assert answers["choose_time_zone"] == "on"
    assert answers["time_zone"] == TimeZone.MAYOTTE


@pytest.fixture
def uploaded_image(settings, tmp_path):
    """What the browser left in the public storage after a direct upload."""
    settings.MEDIA_ROOT = tmp_path
    return storages["public"].save(
        "events/0123456789abcdef0123456789abcdef.png", ContentFile(b"png")
    )


def test_an_uploaded_image_and_its_alternative_text_are_accepted(uploaded_image):
    form = EventDetailsForm(
        data=VALID
        | {"image": uploaded_image, "image_alt": "Une porte ouverte", "image_credit": "Jane Doe"}
    )

    assert form.is_valid(), form.errors
    assert form.event_fields["image"] == uploaded_image
    assert form.event_fields["image_alt"] == "Une porte ouverte"
    assert form.event_fields["image_credit"] == "Jane Doe"


def test_an_image_that_was_never_uploaded_is_refused(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    form = EventDetailsForm(data=VALID | {"image": "events/0123456789abcdef0123456789abcdef.png"})

    assert not form.is_valid()
    assert "image" in form.errors


def test_a_file_stored_outside_the_event_images_is_refused(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    key = storages["public"].save(
        "avatars/0123456789abcdef0123456789abcdef.png", ContentFile(b"p")
    )
    form = EventDetailsForm(data=VALID | {"image": key})

    assert not form.is_valid()
    assert "image" in form.errors


def test_the_alternative_text_and_the_credit_are_dropped_without_an_image():
    form = EventDetailsForm(
        data=VALID | {"image_alt": "Une porte ouverte", "image_credit": "Jane Doe"}
    )

    assert form.is_valid()
    assert form.event_fields["image_alt"] == ""
    assert form.event_fields["image_credit"] == ""


@pytest.mark.django_db
def test_the_form_prefilled_from_an_event_hands_back_its_image(event, uploaded_image):
    event.image = uploaded_image
    event.image_alt = "Une porte ouverte"
    event.image_credit = "Jane Doe"

    answers = EventDetailsForm(event=event).initial

    assert answers["image"] == uploaded_image
    assert answers["image_alt"] == "Une porte ouverte"
    assert answers["image_credit"] == "Jane Doe"
