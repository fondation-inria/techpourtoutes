from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from waffle.testutils import override_switch


@pytest.mark.django_db
def test_login_request_get_renders_form(client):
    response = client.get(reverse("login_request"))

    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_login_request_get_with_safe_next_propagates_to_template(client):
    response = client.get(reverse("login_request") + "?next=/mentorer/")

    assert response.status_code == 200
    assert response.context["next"] == "/mentorer/"


@pytest.mark.django_db
def test_login_request_get_strips_external_next(client):
    response = client.get(reverse("login_request") + "?next=https://evil.com/x")

    assert response.status_code == 200
    assert response.context["next"] == ""


@pytest.mark.django_db
def test_login_request_get_with_back_param_propagates_to_template(client):
    response = client.get(reverse("login_request") + "?back=/mentorer/")

    assert response.status_code == 200
    assert response.context["back"] == "/mentorer/"


@pytest.mark.django_db
def test_login_request_get_strips_external_back(client):
    response = client.get(reverse("login_request") + "?back=https://evil.com/x")

    assert response.status_code == 200
    assert response.context["back"] == ""


@pytest.mark.django_db
def test_login_request_get_ignores_referer_for_back(client):
    response = client.get(reverse("login_request"), HTTP_REFERER="/mentorer/")

    assert response.status_code == 200
    assert response.context["back"] == ""


@pytest.mark.django_db
def test_login_request_close_button_points_to_back(client):
    response = client.get(reverse("login_request") + "?back=/mentorer/")

    html = response.content.decode()
    close_link_index = html.find('aria-label="Fermer"')
    assert 'href="/mentorer/"' in html[max(0, close_link_index - 700) : close_link_index]


@pytest.mark.django_db
def test_login_request_hides_beneficiary_button_when_switch_off(client):
    response = client.get(reverse("login_request"))

    assert "Je veux bénéficier du programme" not in response.content.decode()


@pytest.mark.django_db
def test_login_request_shows_beneficiary_button_when_switch_active(client):
    with override_switch("beneficiary_mode", active=True):
        response = client.get(reverse("login_request"))

    assert "Je veux bénéficier du programme" in response.content.decode()


@pytest.mark.django_db
def test_login_request_get_renders_next_hidden_input(client):
    response = client.get(reverse("login_request") + "?next=/mentorer/")

    assert 'name="next" value="/mentorer/"' in response.content.decode()


@pytest.mark.django_db
def test_login_request_get_while_authenticated_redirects_to_account(client, pro):
    client.force_login(pro)

    response = client.get(reverse("login_request"))

    assert response.status_code == 302
    assert response["Location"] == reverse("account")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_with_known_email_sends_code(client, pro):
    response = client.post(reverse("login_request"), data={"email": pro.email})

    assert response.status_code == 302
    assert response["Location"] == reverse("login_code")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [pro.email]
    pro.refresh_from_db()
    assert pro.login_code_hash != ""


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@patch("techpourtoutes.models.user.generate_numeric_code", return_value="123456")
def test_login_request_post_email_contains_the_code(_code, client, pro):
    client.post(reverse("login_request"), data={"email": pro.email})

    assert "123456" in mail.outbox[0].alternatives[0][0]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_for_pro_sends_vouvoiement_email(client, pro):
    client.post(reverse("login_request"), data={"email": pro.email})

    assert mail.outbox[0].subject == "Votre code de connexion à TechPourToutes"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_with_unknown_email_sends_nothing(client):
    response = client.post(reverse("login_request"), data={"email": "ghost@example.com"})

    assert response.status_code == 302
    assert response["Location"] == reverse("login_code")
    assert mail.outbox == []


@pytest.mark.django_db
def test_login_request_post_stores_safe_next_in_session(client, pro):
    client.post(reverse("login_request"), data={"email": pro.email, "next": "/mentorer/"})

    assert client.session["login_next"] == "/mentorer/"


@pytest.mark.django_db
def test_login_request_post_strips_external_next_from_session(client, pro):
    client.post(reverse("login_request"), data={"email": pro.email, "next": "https://evil.com/x"})

    assert client.session["login_next"] == ""


@pytest.mark.django_db
def test_login_request_post_with_back_carries_it_to_code_page(client):
    response = client.post(
        reverse("login_request"), data={"email": "ghost@example.com", "back": "/mentorer/"}
    )

    assert response.status_code == 302
    assert response["Location"] == f"{reverse('login_code')}?back=%2Fmentorer%2F"


@pytest.mark.django_db
def test_login_request_post_strips_external_back(client):
    response = client.post(
        reverse("login_request"),
        data={"email": "ghost@example.com", "back": "https://evil.com/x"},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("login_code")


@pytest.mark.django_db
def test_login_request_post_from_code_page_shows_resend_message(client):
    from django.conf import settings

    referer = f"{settings.SITE_URL}{reverse('login_code')}"
    response = client.post(
        reverse("login_request"),
        data={"email": "ghost@example.com"},
        HTTP_REFERER=referer,
    )

    assert response.status_code == 302
    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Un nouveau code a été envoyé par mail." in m for m in stored)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_with_inactive_user_sends_nothing(client, inactive_user):
    response = client.post(reverse("login_request"), data={"email": inactive_user.email})

    assert response.status_code == 302
    assert response["Location"] == reverse("login_code")
    assert mail.outbox == []


@pytest.mark.django_db
def test_sidebar_login_link_carries_current_page_as_back(client):
    from urllib.parse import quote

    response = client.get(reverse("mentor_landing"))

    assert response.status_code == 200
    expected_href = f"{reverse('login_request')}?back={quote(reverse('mentor_landing'))}"
    assert expected_href in response.content.decode()


def _start_login(client, email, next_url=""):
    session = client.session
    session["login_email"] = email
    if next_url:
        session["login_next"] = next_url
    session.save()


@pytest.mark.django_db
def test_login_code_without_session_redirects(client):
    response = client.get(reverse("login_code"))

    assert response.status_code == 302
    assert response["Location"] == reverse("login_request")


@pytest.mark.django_db
def test_login_code_with_session_renders_masked_email(client):
    _start_login(client, "alice@example.com")

    response = client.get(reverse("login_code"))

    assert response.status_code == 200
    assert "form" in response.context
    assert response.context["masked_recipient"] in response.content.decode()


@pytest.mark.django_db
def test_login_code_while_authenticated_redirects_to_account(client, pro):
    client.force_login(pro)

    response = client.get(reverse("login_code"))

    assert response.status_code == 302
    assert response["Location"] == reverse("account")


@pytest.mark.django_db
def test_login_code_post_valid_logs_user_in(client, pro):
    code = pro.issue_login_code()
    _start_login(client, pro.email)

    response = client.post(reverse("login_code"), data={"code": code})

    assert response.status_code == 302
    assert response["Location"] == reverse("account")
    assert client.session.get("_auth_user_id") == str(pro.pk)
    assert "login_email" not in client.session
    pro.refresh_from_db()
    assert pro.login_code_hash == ""


@pytest.mark.django_db
def test_login_code_post_valid_redirects_to_session_next(client, pro):
    code = pro.issue_login_code()
    _start_login(client, pro.email, next_url="/mentorer/")

    response = client.post(reverse("login_code"), data={"code": code})

    assert response.status_code == 302
    assert response["Location"] == "/mentorer/"


@pytest.mark.django_db
def test_login_code_post_wrong_code_shows_error(client, pro):
    pro.issue_login_code()
    _start_login(client, pro.email)

    response = client.post(reverse("login_code"), data={"code": "000000"})

    assert response.status_code == 200
    assert response.context["form"].errors["code"]
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_login_code_post_expired_code_does_not_log_in(client, pro):
    code = pro.issue_login_code()
    pro.login_code_expires_at = timezone.now() - timedelta(minutes=1)
    pro.save()
    _start_login(client, pro.email)

    response = client.post(reverse("login_code"), data={"code": code})

    assert response.status_code == 200
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_login_code_post_clears_code_after_max_attempts(client, pro):
    from techpourtoutes.models.user import VERIFICATION_CODE_MAX_ATTEMPTS

    pro.issue_login_code()
    pro.login_code_attempts = VERIFICATION_CODE_MAX_ATTEMPTS - 1
    pro.save()
    _start_login(client, pro.email)

    client.post(reverse("login_code"), data={"code": "000000"})

    pro.refresh_from_db()
    assert pro.login_code_hash == ""


@pytest.mark.django_db
def test_login_code_close_button_points_to_back(client):
    _start_login(client, "alice@example.com")

    response = client.get(reverse("login_code") + "?back=/mentorer/")

    html = response.content.decode()
    close_link_index = html.find('aria-label="Fermer"')
    assert 'href="/mentorer/"' in html[max(0, close_link_index - 700) : close_link_index]


@pytest.mark.django_db
def test_login_verify_with_valid_token_logs_user_in(client, pro):
    plaintext = pro.issue_login_token()

    response = client.get(reverse("login_verify", args=[plaintext]))

    assert response.status_code == 302
    assert response["Location"] == reverse("account")
    assert client.session.get("_auth_user_id") == str(pro.pk)


@pytest.mark.django_db
def test_login_verify_adds_success_message(client, pro):
    plaintext = pro.issue_login_token()

    response = client.get(reverse("login_verify", args=[plaintext]))

    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Bienvenue !" in m for m in stored)


@pytest.mark.django_db
def test_login_verify_redirects_to_safe_next(client, pro):
    plaintext = pro.issue_login_token()

    response = client.get(reverse("login_verify", args=[plaintext]) + "?next=/mentorer/")

    assert response.status_code == 302
    assert response["Location"] == "/mentorer/"


@pytest.mark.django_db
def test_login_verify_strips_external_next(client, pro):
    plaintext = pro.issue_login_token()

    response = client.get(reverse("login_verify", args=[plaintext]) + "?next=https://evil.com/")

    assert response.status_code == 302
    assert response["Location"] == reverse("account")


@pytest.mark.django_db
def test_login_verify_with_garbage_token_redirects_to_login(client):
    response = client.get(reverse("login_verify", args=["not-a-token"]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login_request"))
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_login_verify_with_expired_token_does_not_log_in(client, pro):
    plaintext = pro.issue_login_token()
    pro.login_token_expires_at = timezone.now() - timedelta(minutes=1)
    pro.save()

    response = client.get(reverse("login_verify", args=[plaintext]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login_request"))
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_login_verify_with_already_used_token_does_not_log_in(client, pro):
    plaintext = pro.issue_login_token()
    client.get(reverse("login_verify", args=[plaintext]))
    client.logout()

    response = client.get(reverse("login_verify", args=[plaintext]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login_request"))
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_login_verify_while_another_user_authenticated_logs_them_out_and_logs_in_token_user(
    client, pro
):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    other_user = User.objects.create_user(
        username="other@example.com",
        email="other@example.com",
        first_name="Other",
        last_name="User",
    )
    plaintext = pro.issue_login_token()
    client.force_login(other_user)

    response = client.get(reverse("login_verify", args=[plaintext]))

    assert response.status_code == 302
    assert client.session.get("_auth_user_id") == str(pro.pk)


@pytest.mark.django_db
def test_login_verify_invalid_token_preserves_next(client):
    response = client.get(reverse("login_verify", args=["garbage"]) + "?next=/mentorer/")

    assert response.status_code == 302
    assert "next=%2Fmentorer%2F" in response["Location"]


@pytest.mark.django_db
def test_logout_post_logs_user_out(client, pro):
    client.force_login(pro)
    assert client.session.get("_auth_user_id") == str(pro.pk)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response["Location"] == "/"
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_logout_adds_success_message(client, pro):
    client.force_login(pro)

    response = client.post(reverse("logout"))

    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Au revoir - Déconnexion réalisée avec succès" in m for m in stored)


@pytest.mark.django_db
def test_logout_get_not_allowed(client, pro):
    client.force_login(pro)

    response = client.get(reverse("logout"))

    assert response.status_code == 405


@pytest.mark.django_db
def test_login_to_jobirl_requires_login(client):
    response = client.get(reverse("login_to_jobirl"))

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_login_to_jobirl_for_non_mentor_renders_error(client, db):
    from techpourtoutes.models import User

    user = User.objects.create_user(
        username="plain@example.com",
        email="plain@example.com",
        first_name="Plain",
        last_name="User",
    )
    client.force_login(user)

    response = client.get(reverse("login_to_jobirl"))

    assert response.status_code == 200
    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("mentor" in m.lower() for m in stored)


@pytest.mark.django_db
@override_settings(JOBIRL_URL="https://jobirl.test")
def test_login_to_jobirl_redirects_to_jobirl_url(client, pro):
    with patch("techpourtoutes.views.auth_views.RefreshAccessToken") as MockRefresh:
        MockRefresh.return_value.success = True
        MockRefresh.return_value.failure = False
        MockRefresh.return_value.token = "new-token-xyz"
        client.force_login(pro)

        response = client.get(reverse("login_to_jobirl"))

    assert response.status_code == 302
    assert response["Location"] == "https://jobirl.test/techpourtoutes/auth/new-token-xyz"


@pytest.mark.django_db
def test_login_to_jobirl_shows_error_on_service_failure(client, pro):
    with patch("techpourtoutes.views.auth_views.RefreshAccessToken") as MockRefresh:
        MockRefresh.return_value.success = False
        MockRefresh.return_value.failure = True
        MockRefresh.return_value.errors = ["Erreur de connexion à Jobirl"]
        client.force_login(pro)

        response = client.get(reverse("login_to_jobirl"))

    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Erreur de connexion à Jobirl" in m for m in stored)
    assert response.status_code == 302
    assert response["Location"] == reverse("account")


@pytest.mark.django_db
@override_settings(JOBIRL_URL="https://jobirl.test")
def test_login_to_jobirl_redirects_to_jobirl_url_for_beneficiary(client, beneficiary):
    with patch("techpourtoutes.views.auth_views.RefreshAccessToken") as MockRefresh:
        MockRefresh.return_value.success = True
        MockRefresh.return_value.failure = False
        MockRefresh.return_value.token = "new-token-xyz"
        client.force_login(beneficiary)

        response = client.get(reverse("login_to_jobirl"))

    assert response.status_code == 302
    assert response["Location"] == "https://jobirl.test/techpourtoutes/auth/new-token-xyz"
