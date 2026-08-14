import importlib

import pytest
from django.test import override_settings
from django.urls import clear_url_caches, reverse


@pytest.mark.django_db
def test_admin_mounts_at_configured_url(client):
    import conf.urls

    try:
        with override_settings(ADMIN_URL="secret-mgmt"):
            importlib.reload(conf.urls)
            clear_url_caches()
            # The configured path resolves (redirects to login); the default does not exist.
            assert client.get("/secret-mgmt/").status_code != 404
            assert client.get("/admin/").status_code == 404
    finally:
        importlib.reload(conf.urls)
        clear_url_caches()


@pytest.mark.django_db
def test_admin_requires_verified_otp_device(client, admin_pro):
    client.force_login(admin_pro)  # authenticated, but no verified second factor
    assert client.get(reverse("admin:index")).status_code == 302


@pytest.mark.django_db
def test_admin_accessible_with_verified_otp_device(verified_admin_client):
    assert verified_admin_client.get(reverse("admin:index")).status_code == 200


@pytest.mark.django_db
def test_admin_2fa_can_be_disabled_outside_debug(client, admin_pro):
    client.force_login(admin_pro)  # authenticated, no verified second factor
    with override_settings(DISABLE_ADMIN_2FA=True):
        assert client.get(reverse("admin:index")).status_code == 200
