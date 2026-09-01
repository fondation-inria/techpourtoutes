from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone


def build_event(pro, **overrides):
    from techpourtoutes.models import Event

    start = timezone.localdate() + timedelta(days=30)
    fields = {
        "title": "Portes ouvertes",
        "organizer": "École 42",
        "category": Event.Category.OPEN_HOUSE,
        "start_date": start,
        "end_date": start,
        "start_time": time(9, 0),
        "end_time": time(18, 0),
        "location_type": Event.LocationType.ONLINE,
        "reservation_type": Event.ReservationType.OPEN,
        "price": Decimal("0"),
    }
    return Event(created_by=pro, **{**fields, **overrides})


@pytest.mark.django_db
def test_event_waits_for_validation_when_created(pro):
    from techpourtoutes.models import Event

    event = build_event(pro)
    event.save()

    assert event.status == Event.Status.PENDING
    assert list(pro.events.all()) == [event]
    assert event.organizer == "École 42"
    assert str(event) == "Portes ouvertes"


@pytest.mark.django_db
def test_event_category_label_falls_back_to_the_free_text(pro):
    from techpourtoutes.models import Event

    listed = build_event(pro, category=Event.Category.HACKATHON)
    free = build_event(pro, category="Rencontre d'anciennes élèves")

    assert listed.category_label == "Hackathon"
    assert free.category_label == "Rencontre d'anciennes élèves"


@pytest.mark.django_db
def test_event_rejects_an_end_date_before_its_start_date(pro):
    start = timezone.localdate() + timedelta(days=30)

    with pytest.raises(ValidationError):
        build_event(pro, start_date=start, end_date=start - timedelta(days=1)).save()


@pytest.mark.django_db
def test_event_rejects_an_end_time_before_its_start_time_on_a_single_day(pro):
    with pytest.raises(ValidationError):
        build_event(pro, start_time=time(18, 0), end_time=time(9, 0)).save()


@pytest.mark.django_db
def test_event_keeps_an_address_the_geocoding_api_never_resolved(pro):
    """The API only feeds the autocomplete: what the user typed is enough to save."""
    from techpourtoutes.models import Event

    event = build_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        address="Salle des fêtes, derrière la mairie",
    )
    event.save()

    assert event.address == "Salle des fêtes, derrière la mairie"
    assert event.latitude is None
    assert event.longitude is None
    assert event.ban_id == ""


@pytest.mark.django_db
def test_past_and_upcoming_split_events_on_their_end_date(pro):
    from techpourtoutes.models import Event

    today = timezone.localdate()
    over = build_event(
        pro, start_date=today - timedelta(days=3), end_date=today - timedelta(days=1)
    )
    over.save()
    ongoing = build_event(pro, start_date=today - timedelta(days=1), end_date=today)
    ongoing.save()
    later = build_event(
        pro, start_date=today + timedelta(days=1), end_date=today + timedelta(days=1)
    )
    later.save()

    assert list(Event.objects.past()) == [over]
    assert list(Event.objects.upcoming()) == [ongoing, later]


@pytest.mark.django_db
def test_approved_returns_only_the_validated_events(pro):
    from techpourtoutes.models import Event

    approved = build_event(pro, status=Event.Status.APPROVED)
    approved.save()
    build_event(pro, status=Event.Status.REJECTED).save()
    build_event(pro).save()

    assert list(Event.objects.approved()) == [approved]


@pytest.mark.django_db
def test_event_history_records_the_validation(event):
    from techpourtoutes.models import Event

    event.status = Event.Status.APPROVED
    event.save()

    assert event.history.count() == 2
    assert event.history.first().status == Event.Status.APPROVED
    assert event.history.last().status == Event.Status.PENDING
