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
