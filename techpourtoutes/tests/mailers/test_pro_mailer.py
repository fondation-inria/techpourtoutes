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
def test_new_engagement_sends_email_to_pro(pro):
    ProMailer.new_engagement(pro=pro)

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
