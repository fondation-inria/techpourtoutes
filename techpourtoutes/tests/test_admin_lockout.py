import pytest
from django.test import override_settings
from django.urls import reverse

CREDS = {"username": "ghost@example.com", "password": "wrong"}


@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=3)
@pytest.mark.django_db
def test_admin_login_locks_out_after_repeated_failures(client):
    url = reverse("admin:login")
    for _ in range(3):
        client.post(url, CREDS, HTTP_X_FORWARDED_FOR="9.9.9.9")
    blocked = client.post(url, CREDS, HTTP_X_FORWARDED_FOR="9.9.9.9")
    assert blocked.status_code == 429


@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=3)
@pytest.mark.django_db
def test_admin_lockout_is_scoped_per_ip(client):
    url = reverse("admin:login")
    for _ in range(3):
        client.post(url, CREDS, HTTP_X_FORWARDED_FOR="9.9.9.9")
    assert client.post(url, CREDS, HTTP_X_FORWARDED_FOR="9.9.9.9").status_code == 429
    # same username from another IP is not locked (no global account lock-out DoS)
    assert client.post(url, CREDS, HTTP_X_FORWARDED_FOR="8.8.8.8").status_code == 200
