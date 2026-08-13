import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.mailers import AccountMailer


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_sends_confirmation_email_with_vous_form_to_pro(pro):
    AccountMailer.deletion_confirmation(user=pro)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert message.subject == "Confirmation de suppression de votre compte"
    assert pro.first_name in message.body
    assert "vous confirmons" in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_sends_confirmation_email_with_tu_form_to_beneficiary(beneficiary):
    AccountMailer.deletion_confirmation(user=beneficiary)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [beneficiary.email]
    assert message.subject == "Confirmation de suppression de ton compte"
    assert beneficiary.first_name in message.body
    assert "te confirmons" in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_confirmation_sent_from_agir_address_for_pro(pro):
    AccountMailer.deletion_confirmation(user=pro)

    assert mail.outbox[0].from_email == "TechPourToutes <agir@techpourtoutes.io>"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_confirmation_sent_from_bonjour_address_for_beneficiary(beneficiary):
    AccountMailer.deletion_confirmation(user=beneficiary)

    assert mail.outbox[0].from_email == "TechPourToutes <bonjour@techpourtoutes.io>"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_includes_jobirl_information_for_pro_with_jobirl_account(pro):
    pro.jobirl_user_id = 12345
    pro.save()

    AccountMailer.deletion_confirmation(user=pro)

    body = mail.outbox[0].body

    assert "JobIRL" in body
    assert "e-mentorat@jobirl.com" in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_omits_jobirl_information_for_pro_without_jobirl_account(pro):
    AccountMailer.deletion_confirmation(user=pro)

    body = mail.outbox[0].body

    assert "JobIRL" not in body
    assert "e-mentorat@jobirl.com" not in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_includes_jobirl_information_for_beneficiary_with_jobirl_account(
    beneficiary,
):
    beneficiary.jobirl_user_id = 6789
    beneficiary.save()

    AccountMailer.deletion_confirmation(user=beneficiary)

    body = mail.outbox[0].body

    assert "JobIRL" in body
    assert "e-mentorat@jobirl.com" in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_omits_jobirl_information_for_beneficiary_without_jobirl_account(
    beneficiary,
):
    AccountMailer.deletion_confirmation(user=beneficiary)

    body = mail.outbox[0].body

    assert "JobIRL" not in body
    assert "e-mentorat@jobirl.com" not in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_confirmation_attaches_its_brevo_tags(pro):
    AccountMailer.deletion_confirmation(user=pro)

    assert mail.outbox[0].tags == [
        "utilisateur",
        "suppression du compte",
    ]


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    JOBIRL_ACCOUNT_DELETION_RECIPIENTS=["dpo@example.com"],
)
def test_delete_jobirl_account_request_sends_email_to_configured_recipients(pro):
    pro.jobirl_user_id = 12345
    pro.save()

    AccountMailer.request_jobirl_account_deletion(user=pro)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]

    assert message.to == ["dpo@example.com"]
    assert message.subject == "Demande de suppression de données personnelles"

    body = message.body
    assert pro.first_name in body
    assert pro.last_name in body
    assert str(pro.jobirl_user_id) in body


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    JOBIRL_ACCOUNT_DELETION_RECIPIENTS=["dpo@example.com"],
)
def test_delete_jobirl_account_request_attaches_its_brevo_tags(pro):
    AccountMailer.request_jobirl_account_deletion(user=pro)

    assert mail.outbox[0].tags == [
        "interne",
        "suppression du compte",
    ]


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    LATITUDE_ACCOUNT_DELETION_RECIPIENTS=["latitudes@example.com"],
)
def test_delete_latitudes_account_request_sends_email_to_configured_recipients(pro):
    AccountMailer.request_latitudes_account_deletion(user=pro)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]

    assert message.to == ["latitudes@example.com"]
    assert message.subject == "Demande de suppression de données personnelles"

    body = message.body
    assert pro.first_name in body
    assert pro.last_name in body


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    LATITUDE_ACCOUNT_DELETION_RECIPIENTS=["latitudes@example.com"],
)
def test_delete_latitudes_account_request_attaches_its_brevo_tags(pro):
    AccountMailer.request_latitudes_account_deletion(user=pro)

    assert mail.outbox[0].tags == [
        "interne",
        "suppression du compte",
    ]
