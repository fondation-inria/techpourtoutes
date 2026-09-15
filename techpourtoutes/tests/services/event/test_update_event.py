from unittest.mock import patch

import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.models import Event, SavedEvent
from techpourtoutes.services.event.update_event import UpdateEvent

from .test_create_event import valid_forms

locmem = override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    NEW_EVENT_RECIPIENTS=["agir@techpourtoutes.io"],
)


@pytest.mark.django_db
@locmem
def test_the_answers_are_written_back_onto_the_event(event):
    result = UpdateEvent(event=event, forms=valid_forms())

    assert result.success
    event.refresh_from_db()
    assert event.title == "Salon des métiers du numérique"
    assert event.organizer == "Numeum"
    assert event.description == "Une journée pour rencontrer des professionnelles."


@pytest.mark.django_db
@locmem
def test_the_slug_survives_a_renamed_event(event):
    """An indexed URL outlives a corrected title."""
    slug = event.slug

    UpdateEvent(event=event, forms=valid_forms())

    event.refresh_from_db()
    assert event.slug == slug


@pytest.mark.django_db
@locmem
def test_an_event_awaiting_validation_only_tells_the_team(event, beneficiary):
    """It was never published: nobody but the moderation team knows it exists."""
    SavedEvent.objects.create(event=event, beneficiary=beneficiary)

    UpdateEvent(event=event, forms=valid_forms())

    assert [msg.to for msg in mail.outbox] == [["agir@techpourtoutes.io"]]


@pytest.mark.django_db
@locmem
def test_an_approved_event_tells_the_team_its_author_and_everyone_who_saved_it(event, beneficiary):
    event.status = Event.Status.APPROVED
    event.save()
    SavedEvent.objects.create(event=event, beneficiary=beneficiary)

    UpdateEvent(event=event, forms=valid_forms())

    recipients = {tuple(msg.to) for msg in mail.outbox}
    assert recipients == {
        ("agir@techpourtoutes.io",),
        (event.created_by.email,),
        (beneficiary.email,),
    }
    assert all("a été modifié" in msg.subject for msg in mail.outbox)


@pytest.mark.django_db
@locmem
def test_the_mail_to_a_saver_recaps_the_new_details(event, beneficiary):
    event.status = Event.Status.APPROVED
    event.save()
    SavedEvent.objects.create(event=event, beneficiary=beneficiary)

    UpdateEvent(event=event, forms=valid_forms())

    to_beneficiary = next(msg for msg in mail.outbox if msg.to == [beneficiary.email])
    assert to_beneficiary.subject == "L'événement Salon des métiers du numérique a été modifié"
    assert to_beneficiary.from_email == "TechPourToutes <bonjour@techpourtoutes.io>"
    assert beneficiary.first_name in to_beneficiary.body
    assert "8 Boulevard du Port" in to_beneficiary.body
    assert "gratuit" in to_beneficiary.body
    assert "Une journée pour rencontrer des professionnelles." in to_beneficiary.body


@pytest.mark.django_db
@locmem
def test_each_saver_is_mailed_by_her_own_task(event, beneficiary):
    """One task per recipient: a bounce retries that mail alone, not the whole audience."""
    event.status = Event.Status.APPROVED
    event.save()
    SavedEvent.objects.create(event=event, beneficiary=beneficiary)

    with patch(
        "techpourtoutes.services.event.update_event.send_event_updated_email_task"
    ) as mock_task:
        UpdateEvent(event=event, forms=valid_forms())

    mock_task.delay.assert_called_once_with(
        event_pk=str(event.pk), beneficiary_pk=str(beneficiary.pk)
    )
