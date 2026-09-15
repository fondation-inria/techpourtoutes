from datetime import timedelta

import pytest
from django.utils import timezone

from techpourtoutes.forms.event import EventDetailsForm

VALID = {
    "organizer": "Numeum",
    "title": "Salon des métiers du numérique",
    "description": "Une journée pour rencontrer des professionnelles de la tech.",
    "start_date": "2026-10-01",
    "start_time": "09:00",
    "end_date": "2026-10-02",
    "end_time": "18:00",
}


def test_a_complete_form_is_valid():
    assert EventDetailsForm(data=VALID).is_valid()


def test_every_field_is_required():
    form = EventDetailsForm(data={})

    assert not form.is_valid()
    assert set(form.errors) == set(VALID)


def test_an_end_date_before_the_start_date_is_refused():
    form = EventDetailsForm(data=VALID | {"end_date": "2026-09-30"})

    assert not form.is_valid()
    assert "end_date" in form.errors


def test_an_end_time_before_the_start_time_on_a_single_day_is_refused():
    form = EventDetailsForm(
        data=VALID | {"end_date": "2026-10-01", "start_time": "18:00", "end_time": "09:00"}
    )

    assert not form.is_valid()
    assert "end_time" in form.errors


def test_a_single_day_event_may_start_and_end_at_the_same_time():
    form = EventDetailsForm(
        data=VALID | {"end_date": "2026-10-01", "start_time": "09:00", "end_time": "09:00"}
    )

    assert form.is_valid()


def test_an_event_already_over_is_refused():
    form = EventDetailsForm(data=VALID | {"start_date": "2020-01-01", "end_date": "2020-01-02"})

    assert not form.is_valid()
    assert "end_date" in form.errors


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
