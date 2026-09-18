import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.mailers import ProMailer


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_sends_email_to_pro(pro):
    ProMailer.welcome(pro=pro, token="tok-abc")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert "Bienvenue" in message.subject
    assert pro.first_name in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_includes_account_login_url(pro):
    ProMailer.welcome(pro=pro, token="tok-abc")

    assert "/se-connecter/token/tok-abc" in mail.outbox[0].body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_engagement_added_sends_email_to_pro(pro):
    ProMailer.engagement_added(pro=pro)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert "Votre nouvelle demande d'engagement" in message.subject
    assert pro.first_name in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_attaches_its_brevo_tags(pro):
    ProMailer.welcome(pro=pro, token="tok-abc")

    assert mail.outbox[0].tags == ["utilisateur", "coalition", "mail de bienvenue"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_event_submitted_confirms_the_event_is_awaiting_validation(event):
    ProMailer.event_submitted(event=event)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [event.created_by.email]
    assert "en cours de validation" in message.subject
    assert event.title in message.body
    assert message.tags == ["utilisateur", "coalition", "événement soumis"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_event_approved_notifies_its_author(event):
    ProMailer.event_approved(event=event, comment="Bravo !")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [event.created_by.email]
    assert "en ligne" in message.subject
    assert event.title in message.body
    assert "Bravo !" in message.body
    assert message.tags == ["utilisateur", "coalition", "événement publié"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_event_approved_comment_is_optional(event):
    ProMailer.event_approved(event=event)

    assert len(mail.outbox) == 1


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_event_rejected_notifies_its_author(event):
    ProMailer.event_rejected(event=event, comment="Adresse incomplète.")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [event.created_by.email]
    assert "refusé" in message.subject
    assert event.title in message.body
    assert "Adresse incomplète." in message.body
    assert message.tags == ["utilisateur", "coalition", "événement refusé"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_event_modification_requested_notifies_its_author(event):
    ProMailer.event_modification_requested(event=event, message="Précisez l'adresse.")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [event.created_by.email]
    assert event.title in message.subject
    assert "Précisez l'adresse." in message.body
    assert message.tags == ["utilisateur", "coalition", "modification demandée"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_event_modification_requested_links_to_the_edit_funnel(event):
    ProMailer.event_modification_requested(event=event, message="Précisez l'adresse.")

    message = mail.outbox[0]
    assert "/se-connecter/token/" in message.body
    assert f"evenements%2F{event.pk}%2Fmodifier%2F" in message.body
    event.created_by.refresh_from_db()
    assert event.created_by.login_token_hash
