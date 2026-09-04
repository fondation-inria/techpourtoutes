import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.models import Event
from techpourtoutes.services.event.moderate_event import ModerateEvent

locmem = override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")


@pytest.mark.django_db
@locmem
def test_approving_publishes_the_event_and_notifies_its_author(event):
    result = ModerateEvent(event=event, status=Event.Status.APPROVED, comment="Bravo !")

    assert result.success
    event.refresh_from_db()
    assert event.status == Event.Status.APPROVED
    message = mail.outbox[0]
    assert message.to == [event.created_by.email]
    assert "en ligne" in message.subject
    assert "Bravo !" in message.body


@pytest.mark.django_db
@locmem
def test_rejecting_notifies_its_author_without_publishing(event):
    result = ModerateEvent(
        event=event, status=Event.Status.REJECTED, comment="Adresse incomplète."
    )

    assert result.success
    event.refresh_from_db()
    assert event.status == Event.Status.REJECTED
    message = mail.outbox[0]
    assert message.to == [event.created_by.email]
    assert "refusé" in message.subject
    assert "Adresse incomplète." in message.body


@pytest.mark.django_db
@locmem
def test_the_comment_is_optional(event):
    result = ModerateEvent(event=event, status=Event.Status.APPROVED)

    assert result.success
    assert len(mail.outbox) == 1


@pytest.mark.django_db
@locmem
def test_an_ungeocoded_physical_event_cannot_be_approved(pro):
    from datetime import time, timedelta
    from decimal import Decimal

    from django.utils import timezone

    start = timezone.localdate() + timedelta(days=30)
    event = Event(
        created_by=pro,
        title="Portes ouvertes",
        organizer="École 42",
        subcategory=Event.Subcategory.OPEN_HOUSE,
        start_date=start,
        end_date=start,
        start_time=time(9, 0),
        end_time=time(18, 0),
        location_type=Event.LocationType.PHYSICAL,
        address="Salle des fêtes",
        access_type=Event.AccessType.OPEN,
        price=Decimal("0"),
    )
    event.save()

    result = ModerateEvent(event=event, status=Event.Status.APPROVED)

    assert result.failure
    event.refresh_from_db()
    assert event.status == Event.Status.PENDING
    assert not mail.outbox
