import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.services.soft_delete_account import SoftDeleteAccount


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_soft_delete_account_deactivates_pro(pro):
    SoftDeleteAccount(user=pro)

    pro.refresh_from_db()
    assert not pro.is_active


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_soft_delete_account_sends_vous_confirmation_and_internal_notice_for_pro(pro):
    pro.jobirl_user_id = 12345
    pro.jobirl_user_token = "tok-abc"
    pro.save()

    SoftDeleteAccount(user=pro)

    assert len(mail.outbox) == 2
    confirmation, internal_notice = mail.outbox
    assert confirmation.to == ["alice@example.com"]
    assert "vous confirmons" in confirmation.body
    assert "JobIRL" in confirmation.body
    assert internal_notice.subject == "Demande de suppression de données personnelles"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_soft_delete_account_deactivates_beneficiary(beneficiary):
    SoftDeleteAccount(user=beneficiary)

    beneficiary.refresh_from_db()
    assert not beneficiary.is_active


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_soft_delete_account_sends_only_tu_confirmation_for_beneficiary(beneficiary):
    SoftDeleteAccount(user=beneficiary)

    assert len(mail.outbox) == 1
    confirmation = mail.outbox[0]
    assert confirmation.to == ["jade@example.com"]
    assert "te confirmons" in confirmation.body
    assert "JobIRL" not in confirmation.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_soft_delete_account_sends_internal_notice_for_beneficiary_with_jobirl_account(
    beneficiary,
):
    beneficiary.jobirl_user_id = 6789
    beneficiary.jobirl_user_token = "tok-xyz"
    beneficiary.save()

    SoftDeleteAccount(user=beneficiary)

    assert len(mail.outbox) == 2
    confirmation, internal_notice = mail.outbox
    assert "te confirmons" in confirmation.body
    assert "JobIRL" in confirmation.body
    assert internal_notice.subject == "Demande de suppression de données personnelles"
