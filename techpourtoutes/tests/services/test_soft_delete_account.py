import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.models import Pro
from techpourtoutes.services.soft_delete_account import SoftDeleteAccount

pytestmark = pytest.mark.django_db

mails_are_captured = override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    COALITION_ACCOUNT_DELETION_RECIPIENTS=["dpo@example.com"],
)


@mails_are_captured
def test_soft_delete_account_anonymizes_the_user(pro):
    result = SoftDeleteAccount(user=pro)

    assert result.success
    pro.refresh_from_db()
    assert not pro.is_active
    assert pro.first_name == ""
    assert pro.email == f"deleted_{pro.pk}@deleted.local"


@mails_are_captured
def test_soft_delete_account_mails_the_address_it_is_about_to_erase(pro):
    original_email = pro.email
    original_first_name = pro.first_name

    SoftDeleteAccount(user=pro)

    confirmation = next(m for m in mail.outbox if m.to == [original_email])
    assert confirmation.subject == "Confirmation de suppression de votre compte"
    assert original_first_name in confirmation.body


@mails_are_captured
def test_soft_delete_account_notifies_internal_recipients_with_the_original_identity(pro):
    pro.jobirl_user_id = 8675309
    pro.save()
    original_first_name = pro.first_name
    original_last_name = pro.last_name

    SoftDeleteAccount(user=pro)

    internal = next(m for m in mail.outbox if m.to == ["dpo@example.com"])
    assert internal.subject == "Demande de suppression de données personnelles"
    assert original_first_name in internal.body
    assert original_last_name in internal.body
    assert "8675309" in internal.body


@mails_are_captured
def test_soft_delete_account_mentions_jobirl_only_for_mentors(pro):
    pro.engagements = [Pro.Engagement.MENTOR]
    pro.save()
    original_email = pro.email

    SoftDeleteAccount(user=pro)

    confirmation = next(m for m in mail.outbox if m.to == [original_email])
    assert "JobIRL" in confirmation.body
