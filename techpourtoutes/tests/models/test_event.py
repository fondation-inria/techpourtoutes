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
        "subcategory": Event.Subcategory.OPEN_HOUSE,
        "start_date": start,
        "end_date": start,
        "start_time": time(9, 0),
        "end_time": time(18, 0),
        "location_type": Event.LocationType.ONLINE,
        "access_type": Event.AccessType.OPEN,
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
def test_event_subcategory_label_falls_back_to_the_free_text(pro):
    from techpourtoutes.models import Event

    listed = build_event(pro, subcategory=Event.Subcategory.HACKATHON)
    free = build_event(pro, subcategory="Rencontre d'anciennes élèves")

    assert listed.subcategory_label == "Hackathon"
    assert free.subcategory_label == "Rencontre d'anciennes élèves"


def test_every_subcategory_belongs_to_exactly_one_category():
    from techpourtoutes.models import Event

    listed = [sub for subs in Event.SUBCATEGORIES.values() for sub in subs]

    assert sorted(listed) == sorted(Event.Subcategory.values)


@pytest.mark.django_db
def test_event_category_is_derived_from_its_subcategory(pro):
    from techpourtoutes.models import Event

    event = build_event(pro, subcategory=Event.Subcategory.JOB_DATING)

    assert event.category == Event.Category.EMPLOYMENT
    assert event.category_label == "Emploi"


@pytest.mark.django_db
def test_a_free_text_subcategory_lands_in_the_category_holding_other(pro):
    from techpourtoutes.models import Event

    event = build_event(pro, subcategory="Rencontre d'anciennes élèves")

    assert event.category == Event.Category.SOCIAL


@pytest.mark.django_db
def test_in_subcategory_brings_the_free_text_back_under_other(pro):
    from techpourtoutes.models import Event

    free = build_event(pro, subcategory="Rencontre d'anciennes élèves")
    free.save()
    other = build_event(pro, subcategory=Event.Subcategory.OTHER)
    other.save()
    build_event(pro, subcategory=Event.Subcategory.CEREMONY).save()

    assert set(Event.objects.in_subcategory(Event.Subcategory.OTHER)) == {free, other}


@pytest.mark.django_db
def test_in_category_returns_the_events_of_all_its_subcategories(pro):
    from techpourtoutes.models import Event

    conference = build_event(pro, subcategory=Event.Subcategory.CONFERENCE)
    conference.save()
    round_table = build_event(pro, subcategory=Event.Subcategory.ROUND_TABLE)
    round_table.save()
    build_event(pro, subcategory=Event.Subcategory.HACKATHON).save()

    assert set(Event.objects.in_category(Event.Category.INFORMATION)) == {conference, round_table}


@pytest.mark.django_db
def test_in_category_includes_the_free_text_where_other_sits(pro):
    from techpourtoutes.models import Event

    free = build_event(pro, subcategory="Rencontre d'anciennes élèves")
    free.save()
    afterwork = build_event(pro, subcategory=Event.Subcategory.AFTERWORK)
    afterwork.save()
    build_event(pro, subcategory=Event.Subcategory.VISIT).save()

    assert set(Event.objects.in_category(Event.Category.SOCIAL)) == {free, afterwork}


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
def test_an_ungeocoded_physical_event_cannot_be_approved(pro):
    """Nothing may go live on a map without coordinates: the admin has to geocode it first."""
    from techpourtoutes.models import Event

    event = build_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        address="Salle des fêtes, derrière la mairie",
        status=Event.Status.APPROVED,
    )

    with pytest.raises(ValidationError):
        event.save()


@pytest.mark.django_db
def test_a_geocoded_physical_event_can_be_approved(event):
    from techpourtoutes.models import Event

    event.status = Event.Status.APPROVED
    event.save()

    assert list(Event.objects.approved()) == [event]


@pytest.mark.django_db
def test_an_online_event_can_be_approved_without_coordinates(pro):
    from techpourtoutes.models import Event

    event = build_event(pro, status=Event.Status.APPROVED)
    event.save()

    assert event.latitude is None
    assert list(Event.objects.approved()) == [event]


@pytest.mark.django_db
def test_event_history_records_the_validation(event):
    from techpourtoutes.models import Event

    event.status = Event.Status.APPROVED
    event.save()

    assert event.history.count() == 2
    assert event.history.first().status == Event.Status.APPROVED
    assert event.history.last().status == Event.Status.PENDING
