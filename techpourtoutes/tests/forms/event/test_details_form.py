from datetime import datetime, time, timedelta

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.utils import timezone

from techpourtoutes.forms.event import EventDetailsForm

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


@pytest.fixture
def at_three_pm_today(monkeypatch):
    now = timezone.make_aware(datetime.combine(timezone.localdate(), time(15, 0)))
    monkeypatch.setattr(timezone, "now", lambda: now)


def today_ending_at(end_time):
    today = timezone.localdate().isoformat()
    return VALID | {"start_date": today, "end_date": today, "end_time": end_time}


@pytest.mark.usefixtures("at_three_pm_today")
def test_an_event_that_ended_earlier_today_is_refused():
    form = EventDetailsForm(data=today_ending_at("14:59"))

    assert not form.is_valid()
    assert "end_time" in form.errors


@pytest.mark.usefixtures("at_three_pm_today")
def test_an_event_ending_later_today_is_accepted():
    form = EventDetailsForm(data=today_ending_at("15:00"))

    assert form.is_valid()


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


def test_event_fields_carries_every_answer_of_the_screen():
    form = EventDetailsForm(data=VALID)

    assert form.is_valid()
    assert form.event_fields["title"] == VALID["title"]
    assert set(form.event_fields) == set(EventDetailsForm.base_fields)


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
