from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse


@override_settings(RATELIMIT_LOGIN="2/3600")
@pytest.mark.django_db
def test_login_request_throttled_per_email_across_ips(client):
    get_user_model().objects.create_user(username="cible@example.com", email="cible@example.com")
    url = reverse("login_request")
    for i in range(2):
        response = client.post(
            url, {"email": "cible@example.com"}, HTTP_X_FORWARDED_FOR=f"1.1.1.{i}"
        )
        assert response.status_code == 302
    blocked = client.post(url, {"email": "cible@example.com"}, HTTP_X_FORWARDED_FOR="1.1.1.99")
    assert blocked.status_code == 429
    assert len(mail.outbox) == 2  # bombing capped despite varied IPs


@override_settings(RATELIMIT_EMAIL_CHANGE_RESEND="2/3600")
@patch("techpourtoutes.models.user.generate_email_change_code", return_value="123456")
@pytest.mark.django_db
def test_email_change_resend_throttled_per_ip(_code, client, pro):
    client.force_login(pro)
    pro.set_email_change_code()
    token = pro.issue_email_change_token("new@example.com", "current")
    url = reverse("email_change_resend")
    for _ in range(2):
        response = client.post(url, {"token": token}, HTTP_X_FORWARDED_FOR="2.2.2.2")
        assert response.status_code == 302
    blocked = client.post(url, {"token": token}, HTTP_X_FORWARDED_FOR="2.2.2.2")
    assert blocked.status_code == 429
    assert len(mail.outbox) == 2  # resend bombing capped per IP
