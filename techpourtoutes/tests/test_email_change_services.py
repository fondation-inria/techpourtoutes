import pytest
from django.urls import reverse

from techpourtoutes.services.verify_email_change_code import VerifyEmailChangeCode


@pytest.mark.django_db
def test_verify_wrong_code_fails(pro, mailoutbox):
    pro.set_email_change_code()
    payload = {"stage": "current", "new_email": "new@example.com"}

    result = VerifyEmailChangeCode(user=pro, payload=payload, code="000000")

    assert result.failure
    assert result.errors


@pytest.mark.django_db
def test_verify_locks_after_max_attempts(pro, mailoutbox):
    from techpourtoutes.models.user import VERIFICATION_CODE_MAX_ATTEMPTS

    code = pro.set_email_change_code()
    pro.email_change_attempts = VERIFICATION_CODE_MAX_ATTEMPTS - 1
    pro.save()
    payload = {"stage": "current", "new_email": "new@example.com"}

    result = VerifyEmailChangeCode(user=pro, payload=payload, code="000000")

    assert result.failure
    pro.refresh_from_db()
    assert pro.email_change_code_hash == ""
    assert pro.consume_email_change_code(code) is False


@pytest.mark.django_db
def test_verify_current_advances_and_mails_new(pro, mailoutbox):
    code = pro.set_email_change_code()
    previous_hash = pro.email_change_code_hash
    payload = {"stage": "current", "new_email": "new@example.com"}

    result = VerifyEmailChangeCode(user=pro, payload=payload, code=code)

    assert result.success
    assert reverse("email_change_verify") in result.redirect_url
    pro.refresh_from_db()
    assert pro.email_change_code_hash != previous_hash
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["new@example.com"]


@pytest.mark.django_db
def test_verify_new_applies_change(pro, mailoutbox):
    code = pro.set_email_change_code()
    payload = {"stage": "new", "new_email": "new@example.com"}

    result = VerifyEmailChangeCode(user=pro, payload=payload, code=code)

    assert result.success
    assert result.redirect_url == reverse("account")
    pro.refresh_from_db()
    assert pro.email == "new@example.com"
    assert pro.username == "new@example.com"
    assert pro.email_change_code_hash == ""
