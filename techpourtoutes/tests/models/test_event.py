from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

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
    free = build_event(pro, subcategory="Rencontre d'anciennes")

    assert listed.subcategory_label == "Hackathon"
    assert free.subcategory_label == "Rencontre d'anciennes"


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

    event = build_event(pro, subcategory="Rencontre d'anciennes")

    assert event.category == Event.Category.SOCIAL


@pytest.mark.django_db
def test_in_subcategory_brings_the_free_text_back_under_other(pro):
    from techpourtoutes.models import Event

    free = build_event(pro, subcategory="Rencontre d'anciennes")
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

    free = build_event(pro, subcategory="Rencontre d'anciennes")
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
        Event.Subcategory.HACKATHON: "purple",
    }

    for subcategory, color in colors.items():
        assert build_event(pro, subcategory=subcategory).category_color == color


@pytest.mark.django_db
def test_a_free_text_subcategory_takes_the_color_of_the_category_holding_other(pro):
    event = build_event(pro, subcategory="Rencontre d'anciennes")

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
def test_event_keeps_a_venue_with_no_street_address(pro):
    """A POI carries a name and a commune, never a street: the address columns stay empty."""
    from techpourtoutes.models import Event

    event = build_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        poi_name="Station F",
        city="Paris 13e Arrondissement",
        cog_code="75113",
        longitude=2.371699,
        latitude=48.833436,
    )
    event.save()

    assert event.address == ""
    assert event.postal_code == ""


@pytest.mark.django_db
def test_location_label_prefers_the_venue_over_the_address(pro):
    from techpourtoutes.models import Event

    venue = build_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        poi_name="Station F",
        city="Paris 13e Arrondissement",
    )
    address = build_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        address="8 Boulevard du Port",
        postal_code="80000",
        city="Amiens",
    )

    assert venue.location_label == "Station F Paris 13e Arrondissement"
    assert address.location_label == "8 Boulevard du Port 80000 Amiens"


@pytest.mark.django_db
def test_past_and_upcoming_split_events_on_their_end_date(pro):
    """Read at midday, so the split falls on the date alone: an event ending today at 18:00
    is still to come. Where the two fall on the same day, the end time decides — that is the
    next test's business, and the clock the suite runs on must not decide it here."""
    from techpourtoutes.models import Event

    today = timezone.localdate()
    midday = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
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

    with patch("django.utils.timezone.localtime", return_value=midday):
        assert list(Event.objects.past()) == [over]
        assert list(Event.objects.upcoming()) == [ongoing, later]


@pytest.mark.django_db
def test_past_and_upcoming_split_same_day_events_on_their_end_time(pro):
    from techpourtoutes.models import Event

    now = timezone.localtime()
    just_ended = build_event(
        pro,
        start_date=now.date(),
        end_date=now.date(),
        start_time=time(0, 0),
        end_time=(now - timedelta(minutes=1)).time(),
    )
    just_ended.save()
    still_ongoing = build_event(
        pro,
        start_date=now.date(),
        end_date=now.date(),
        start_time=time(0, 0),
        end_time=(now + timedelta(minutes=1)).time(),
    )
    still_ongoing.save()

    assert list(Event.objects.past()) == [just_ended]
    assert list(Event.objects.upcoming()) == [still_ongoing]


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
def test_a_physical_event_naming_neither_address_nor_venue_cannot_be_approved(pro):
    """Coordinates alone put a pin on a map with nothing to read next to it."""
    from techpourtoutes.models import Event

    event = build_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        longitude=2.371699,
        latitude=48.833436,
        status=Event.Status.APPROVED,
    )

    with pytest.raises(ValidationError):
        event.save()


@pytest.mark.django_db
def test_a_geocoded_venue_can_be_approved_without_a_street_address(pro):
    from techpourtoutes.models import Event

    event = build_event(
        pro,
        location_type=Event.LocationType.PHYSICAL,
        poi_name="Station F",
        city="Paris 13e Arrondissement",
        cog_code="75113",
        longitude=2.371699,
        latitude=48.833436,
        status=Event.Status.APPROVED,
    )
    event.save()

    assert list(Event.objects.approved()) == [event]


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
def test_has_ended_is_false_before_the_end_date(pro):
    tomorrow = timezone.localdate() + timedelta(days=1)

    event = build_event(pro, start_date=tomorrow, end_date=tomorrow)

    assert event.has_ended is False


@pytest.mark.django_db
def test_has_ended_is_true_after_the_end_date(pro):
    yesterday = timezone.localdate() - timedelta(days=1)

    event = build_event(pro, start_date=yesterday, end_date=yesterday)

    assert event.has_ended is True


@pytest.mark.django_db
def test_has_ended_checks_the_time_when_the_event_ends_today(pro):
    """A date-only comparison would miss this: the event ends today, earlier than now."""
    today = timezone.localdate()

    event = build_event(
        pro, start_date=today, end_date=today, start_time=time(0, 0), end_time=time(0, 1)
    )

    assert event.has_ended is True


@pytest.mark.django_db
def test_is_approved_is_true_only_once_the_event_is_validated(pro):
    from techpourtoutes.models import Event

    assert build_event(pro, status=Event.Status.APPROVED).is_approved is True
    assert build_event(pro, status=Event.Status.PENDING).is_approved is False
    assert build_event(pro, status=Event.Status.REJECTED).is_approved is False


@pytest.mark.django_db
def test_event_history_records_the_validation(event):
    from techpourtoutes.models import Event

    event.status = Event.Status.APPROVED
    event.save()

    assert event.history.count() == 2
    assert event.history.first().status == Event.Status.APPROVED
    assert event.history.last().status == Event.Status.PENDING


@pytest.mark.django_db
def test_event_slug_is_built_from_its_title(pro):
    event = build_event(pro, title="Salon des métiers du numérique")
    event.save()

    assert event.slug == "salon-des-metiers-du-numerique"


@pytest.mark.django_db
def test_event_slug_suffixes_a_title_already_taken(pro):
    build_event(pro, title="Portes ouvertes").save()

    second = build_event(pro, title="Portes ouvertes")
    second.save()

    assert second.slug == "portes-ouvertes-2"


@pytest.mark.django_db
def test_event_slug_never_moves_once_written(pro):
    """An indexed URL outlives a corrected title."""
    event = build_event(pro, title="Portes ouvertes")
    event.save()

    event.title = "Portes ouvertes 2026"
    event.save()

    assert event.slug == "portes-ouvertes"


@pytest.mark.django_db
def test_event_slug_falls_back_when_the_title_slugifies_to_nothing(pro):
    event = build_event(pro, title="★★★")
    event.save()

    assert event.slug == "evenement"


@pytest.mark.django_db(transaction=True)
def test_event_slug_steps_aside_when_a_concurrent_creation_wins_the_insert(pro):
    """A twin lands after this event's validation, so nothing but the unique index can catch
    it. It is committed by another connection, which is what a real race looks like."""
    import threading

    from django.db import connection
    from django.db.models.signals import pre_save

    from techpourtoutes.models import Event

    def create_the_twin_elsewhere(sender, instance, **kwargs):
        pre_save.disconnect(create_the_twin_elsewhere, sender=Event)
        thread = threading.Thread(target=_commit_twin, args=(pro,))
        thread.start()
        thread.join()

    def _commit_twin(pro):
        build_event(pro, title="Portes ouvertes").save()
        connection.close()

    pre_save.connect(create_the_twin_elsewhere, sender=Event)
    try:
        event = build_event(pro, title="Portes ouvertes")
        event.save()
    finally:
        pre_save.disconnect(create_the_twin_elsewhere, sender=Event)

    assert event.slug == "portes-ouvertes-2"
    assert Event.objects.filter(slug="portes-ouvertes").count() == 1
    assert Event.objects.count() == 2


@pytest.mark.django_db
def test_pending_returns_only_the_events_awaiting_validation(pro):
    from techpourtoutes.models import Event

    waiting = build_event(pro)
    waiting.save()
    build_event(pro, status=Event.Status.APPROVED).save()
    build_event(pro, status=Event.Status.REJECTED).save()

    assert list(Event.objects.pending()) == [waiting]


@pytest.mark.django_db
def test_visible_to_hides_an_event_awaiting_validation_from_everyone_but_its_author(
    pro, beneficiary
):
    from django.contrib.auth.models import AnonymousUser

    from techpourtoutes.models import Event, User

    waiting = build_event(pro)
    waiting.save()
    staff = User.objects.create_user(
        username="staff@example.com",
        email="staff@example.com",
        first_name="Ada",
        last_name="Moderatrice",
        is_staff=True,
    )

    assert list(Event.objects.visible_to(pro)) == [waiting]
    assert list(Event.objects.visible_to(staff)) == [waiting]
    assert not Event.objects.visible_to(beneficiary).exists()
    assert not Event.objects.visible_to(AnonymousUser()).exists()


@pytest.mark.django_db
def test_visible_to_shows_an_approved_event_to_anyone(pro):
    from django.contrib.auth.models import AnonymousUser

    from techpourtoutes.models import Event

    approved = build_event(pro, status=Event.Status.APPROVED)
    approved.save()

    assert list(Event.objects.visible_to(AnonymousUser())) == [approved]


@pytest.mark.django_db
def test_visible_to_hides_a_rejected_event_from_its_author(pro):
    """Only the moderation team sees what it turned down."""
    from techpourtoutes.models import Event

    build_event(pro, status=Event.Status.REJECTED).save()

    assert not Event.objects.visible_to(pro).exists()


@pytest.mark.django_db
def test_visible_to_asks_the_database_once(pro, django_assert_num_queries):
    """Nobody is fetched to find out whether the visitor is a pro: her own id is the key."""
    from techpourtoutes.models import Event

    build_event(pro, status=Event.Status.APPROVED).save()

    with django_assert_num_queries(1):
        list(Event.objects.visible_to(pro))


@pytest.mark.django_db
def test_is_organized_by_recognises_the_pro_who_submitted_the_event(pro, beneficiary):
    from django.contrib.auth.models import AnonymousUser

    event = build_event(pro)
    event.save()

    assert event.is_organized_by(pro)
    assert not event.is_organized_by(beneficiary)
    assert not event.is_organized_by(AnonymousUser())


@pytest.mark.django_db
def test_fill_from_writes_the_funnel_answers_onto_the_columns(pro):
    from techpourtoutes.models import Event
    from techpourtoutes.tests.services.event.test_create_event import valid_forms

    event = Event(created_by=pro)
    event.fill_from(valid_forms())

    assert event.title == "Salon des métiers du numérique"
    assert event.subcategory == Event.Subcategory.SALON
    assert event.city == "Amiens"
    assert event.price == 0


@pytest.mark.django_db
def test_fill_from_leaves_out_the_answers_that_are_not_columns(pro):
    """`pricing` is the branch she answered and `address_api_down` how the address was
    obtained: neither is a field on the event."""
    from techpourtoutes.models import Event
    from techpourtoutes.tests.services.event.test_create_event import valid_forms

    event = Event(created_by=pro)
    event.fill_from(valid_forms())

    assert not hasattr(event, "pricing")
    assert not hasattr(event, "address_api_down")
