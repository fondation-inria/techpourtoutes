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
