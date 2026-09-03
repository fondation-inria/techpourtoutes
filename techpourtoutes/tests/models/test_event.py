from datetime import date, time, timedelta
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
def test_event_category_color_follows_its_category(pro):
    from techpourtoutes.models import Event

    colors = {
        Event.Subcategory.CONFERENCE: "orange",
        Event.Subcategory.JOB_DATING: "yellow",
        Event.Subcategory.OPEN_HOUSE: "green",
        Event.Subcategory.AFTERWORK: "purple",
        Event.Subcategory.HACKATHON: "blue",
    }

    for subcategory, color in colors.items():
        assert build_event(pro, subcategory=subcategory).category_color == color


@pytest.mark.django_db
def test_a_free_text_subcategory_takes_the_color_of_the_category_holding_other(pro):
    event = build_event(pro, subcategory="Rencontre d'anciennes élèves")

    assert event.category_color == "purple"


@pytest.mark.django_db
def test_date_range_label_names_a_single_day_once(pro):
    event = build_event(pro, start_date=date(2026, 6, 12), end_date=date(2026, 6, 12))

    assert event.date_range_label == "le 12 juin 2026"


@pytest.mark.django_db
def test_date_range_label_writes_a_shared_month_once(pro):
    event = build_event(pro, start_date=date(2026, 6, 12), end_date=date(2026, 6, 14))

    assert event.date_range_label == "du 12 au 14 juin 2026"


@pytest.mark.django_db
def test_date_range_label_repeats_the_month_when_it_changes(pro):
    event = build_event(pro, start_date=date(2026, 6, 30), end_date=date(2026, 7, 2))

    assert event.date_range_label == "du 30 juin au 2 juillet 2026"


@pytest.mark.django_db
def test_date_range_label_repeats_the_year_when_it_changes(pro):
    event = build_event(pro, start_date=date(2026, 12, 30), end_date=date(2027, 1, 2))

    assert event.date_range_label == "du 30 décembre 2026 au 2 janvier 2027"


@pytest.mark.django_db
def test_price_label_says_free_rather_than_zero(pro):
    assert build_event(pro, price=Decimal("0")).price_label == "gratuit"


@pytest.mark.django_db
def test_price_label_shows_the_amount_and_hides_empty_cents(pro):
    assert build_event(pro, price=Decimal("20.50")).price_label == "20,50 €"
    assert build_event(pro, price=Decimal("20.00")).price_label == "20 €"


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
