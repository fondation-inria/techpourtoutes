from datetime import timedelta

import pytest
from django.contrib.messages import get_messages
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone


@pytest.mark.django_db
def test_login_request_get_renders_form(client):
    response = client.get(reverse("login_request"))

    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_login_request_get_with_safe_next_propagates_to_template(client):
    response = client.get(reverse("login_request") + "?next=/je-deviens-mentor/")

    assert response.status_code == 200
    assert response.context["next"] == "/je-deviens-mentor/"


@pytest.mark.django_db
def test_login_request_get_strips_external_next(client):
    response = client.get(reverse("login_request") + "?next=https://evil.com/x")

    assert response.status_code == 200
    assert response.context["next"] == ""


@pytest.mark.django_db
def test_login_request_get_while_authenticated_redirects_home(client, mentor):
    client.force_login(mentor)

    response = client.get(reverse("login_request"))

    assert response.status_code == 302
    assert response["Location"] == "/"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_with_known_email_sends_link(client, mentor):
    response = client.post(reverse("login_request"), data={"email": mentor.email})

    assert response.status_code == 302
    assert response["Location"] == reverse("login_email_sent")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [mentor.email]
    assert "/se-connecter/token/" in mail.outbox[0].alternatives[0][0]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_with_unknown_email_sends_nothing(client):
    response = client.post(reverse("login_request"), data={"email": "ghost@example.com"})

    assert response.status_code == 302
    assert response["Location"] == reverse("login_email_sent")
    assert mail.outbox == []


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_with_inactive_user_sends_nothing(client, inactive_user):
    response = client.post(reverse("login_request"), data={"email": inactive_user.email})

    assert response.status_code == 302
    assert response["Location"] == reverse("login_email_sent")
    assert mail.outbox == []


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_embeds_safe_next_in_link(client, mentor):
    client.post(
        reverse("login_request"),
        data={"email": mentor.email, "next": "/je-deviens-mentor/"},
    )

    html_body = mail.outbox[0].alternatives[0][0]
    assert "next=%2Fje-deviens-mentor%2F" in html_body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_strips_external_next_from_link(client, mentor):
    client.post(
        reverse("login_request"),
        data={"email": mentor.email, "next": "https://evil.com/x"},
    )

    html_body = mail.outbox[0].alternatives[0][0]
    assert "next=" not in html_body


@pytest.mark.django_db
def test_login_email_sent_without_session_redirects(client):
    response = client.get(reverse("login_email_sent"))

    assert response.status_code == 302
    assert response["Location"] == reverse("login_request")


@pytest.mark.django_db
def test_login_email_sent_with_session_renders_email(client):
    session = client.session
    session["login_email"] = "alice@example.com"
    session.save()

    response = client.get(reverse("login_email_sent"))

    assert response.status_code == 200
    assert "alice@example.com" in response.content.decode()


@pytest.mark.django_db
def test_login_verify_with_valid_token_logs_user_in(client, mentor):
    plaintext = mentor.issue_login_token()

    response = client.get(reverse("login_verify", args=[plaintext]))

    assert response.status_code == 302
    assert response["Location"] == "/"
    assert client.session.get("_auth_user_id") == str(mentor.pk)


@pytest.mark.django_db
def test_login_verify_adds_success_message(client, mentor):
    plaintext = mentor.issue_login_token()

    response = client.get(reverse("login_verify", args=[plaintext]))

    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Bienvenue !" in m for m in stored)


@pytest.mark.django_db
def test_login_verify_redirects_to_safe_next(client, mentor):
    plaintext = mentor.issue_login_token()

    response = client.get(reverse("login_verify", args=[plaintext]) + "?next=/je-deviens-mentor/")

    assert response.status_code == 302
    assert response["Location"] == "/je-deviens-mentor/"


@pytest.mark.django_db
def test_login_verify_strips_external_next(client, mentor):
    plaintext = mentor.issue_login_token()

    response = client.get(reverse("login_verify", args=[plaintext]) + "?next=https://evil.com/")

    assert response.status_code == 302
    assert response["Location"] == "/"


@pytest.mark.django_db
def test_login_verify_with_garbage_token_redirects_to_login(client):
    response = client.get(reverse("login_verify", args=["not-a-token"]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login_request"))
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_login_verify_with_expired_token_does_not_log_in(client, mentor):
    plaintext = mentor.issue_login_token()
    mentor.login_token_expires_at = timezone.now() - timedelta(minutes=1)
    mentor.save()

    response = client.get(reverse("login_verify", args=[plaintext]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login_request"))
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_login_verify_with_already_used_token_does_not_log_in(client, mentor):
    plaintext = mentor.issue_login_token()
    client.get(reverse("login_verify", args=[plaintext]))
    client.logout()

    response = client.get(reverse("login_verify", args=[plaintext]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login_request"))
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_login_verify_while_authenticated_does_not_consume_token(client, mentor):
    plaintext = mentor.issue_login_token()
    client.force_login(mentor)

    response = client.get(reverse("login_verify", args=[plaintext]))

    assert response.status_code == 302
    assert response["Location"] == "/"
    mentor.refresh_from_db()
    assert mentor.login_token_hash != ""


@pytest.mark.django_db
def test_login_verify_invalid_token_preserves_next(client):
    response = client.get(reverse("login_verify", args=["garbage"]) + "?next=/je-deviens-mentor/")

    assert response.status_code == 302
    assert "next=%2Fje-deviens-mentor%2F" in response["Location"]


@pytest.mark.django_db
def test_account_requires_login(client):
    response = client.get(reverse("account"))

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]
    assert "next=" in response["Location"]


@pytest.mark.django_db
def test_account_renders_when_authenticated(client, mentor):
    client.force_login(mentor)

    response = client.get(reverse("account"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_logout_post_logs_user_out(client, mentor):
    client.force_login(mentor)
    assert client.session.get("_auth_user_id") == str(mentor.pk)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response["Location"] == "/"
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_logout_adds_success_message(client, mentor):
    client.force_login(mentor)

    response = client.post(reverse("logout"))

    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Au revoir - Déconnexion réalisée avec succès" in m for m in stored)


@pytest.mark.django_db
def test_logout_get_not_allowed(client, mentor):
    client.force_login(mentor)

    response = client.get(reverse("logout"))

    assert response.status_code == 405
