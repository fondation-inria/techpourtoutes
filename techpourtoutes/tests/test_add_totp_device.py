import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_add_totp_device_creates_confirmed_device_and_prints_secret(pro):
    from django_otp.plugins.otp_totp.models import TOTPDevice

    out = io.StringIO()
    call_command("add_totp_device", pro.email, stdout=out)

    device = TOTPDevice.objects.get(user=pro)
    assert device.confirmed
    assert out.getvalue().strip()  # the TOTP secret, for manual entry in an authenticator app


@pytest.mark.django_db
def test_add_totp_device_unknown_email_errors():
    with pytest.raises(CommandError):
        call_command("add_totp_device", "nobody@example.com")
