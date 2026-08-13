import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.mailers import AuthMailer


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_send_code_sends_email_to_user(pro):
    AuthMailer.login_code(user=pro, code="123456")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert message.subject == "Votre code de connexion à TechPourToutes"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_send_code_body_contains_the_code(pro):
    AuthMailer.login_code(user=pro, code="123456")

    assert "123456" in mail.outbox[0].body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_code_attaches_its_brevo_tags(pro):
    AuthMailer.login_code(user=pro, code="123456")

    assert mail.outbox[0].tags == ["utilisateur", "mail de connexion"]
