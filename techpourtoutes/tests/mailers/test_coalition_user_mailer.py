import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.mailers import CoalitionUserMailer
from techpourtoutes.models import Pro


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_sends_email_to_pro(pro):
    CoalitionUserMailer.welcome(pro=pro, token="tok-abc")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert "Bienvenue" in message.subject
    assert pro.first_name in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_includes_account_login_url(pro):
    CoalitionUserMailer.welcome(pro=pro, token="tok-abc")

    assert "/se-connecter/token/tok-abc" in mail.outbox[0].body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_new_engagement_sends_email_to_pro(pro):
    CoalitionUserMailer.new_engagement(pro=pro)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert "Votre nouvelle demande d'engagement" in message.subject
    assert pro.first_name in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_attaches_its_brevo_tags(pro):
    CoalitionUserMailer.welcome(pro=pro, token="tok-abc")

    assert mail.outbox[0].tags == ["utilisateur", "coalition", "mail de bienvenue"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_sends_confirmation_email_to_user(pro):
    CoalitionUserMailer.delete_account(
        recipient_email=pro.email,
        first_name=pro.first_name,
        engagements=[],
    )

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert message.subject == "Confirmation de suppression de votre compte"
    assert pro.first_name in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_includes_jobirl_information_for_mentor(pro):
    CoalitionUserMailer.delete_account(
        recipient_email=pro.email,
        first_name=pro.first_name,
        engagements=[Pro.Engagement.MENTOR],
    )

    body = mail.outbox[0].body

    assert "JobIRL" in body
    assert "e-mentorat@jobirl.com" in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_omits_jobirl_information_for_non_mentor(pro):
    CoalitionUserMailer.delete_account(
        recipient_email=pro.email,
        first_name=pro.first_name,
        engagements=[],
    )

    body = mail.outbox[0].body

    assert "JobIRL" not in body
    assert "e-mentorat@jobirl.com" not in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_confirmation_attaches_its_brevo_tags(pro):
    CoalitionUserMailer.delete_account(
        recipient_email=pro.email,
        first_name=pro.first_name,
        engagements=[],
    )

    assert mail.outbox[0].tags == [
        "utilisateur",
        "coalition",
        "suppression du compte",
    ]
