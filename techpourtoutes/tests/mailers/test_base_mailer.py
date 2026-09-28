import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.mailers import AuthMailer


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_SUBJECT_PREFIX="[staging] ",
)
def test_send_mail_prefixes_the_subject_outside_production(pro):
    AuthMailer.login_code(user=pro, code="123456")

    assert mail.outbox[0].subject == "[staging] Votre code de connexion à TechPourToutes"


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_SUBJECT_PREFIX="",
)
def test_send_mail_leaves_the_subject_untouched_in_production(pro):
    AuthMailer.login_code(user=pro, code="123456")

    assert mail.outbox[0].subject == "Votre code de connexion à TechPourToutes"
