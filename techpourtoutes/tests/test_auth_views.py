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
def test_login_request_terms_paragraph_uses_vous_for_coalition_referrer(client):
    from urllib.parse import quote

    response = client.get(reverse("login_request") + "?back=" + quote(reverse("mentor_landing")))

    assert "vous reconnaissez avoir compris et accepté" in response.content.decode()


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
def test_login_request_post_with_known_email_sends_link(client, pro):
    response = client.post(reverse("login_request"), data={"email": pro.email})

    assert response.status_code == 302
    assert response["Location"] == reverse("login_email_sent")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [pro.email]
    assert "/se-connecter/token/" in mail.outbox[0].alternatives[0][0]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_for_pro_sends_vouvoiement_email(client, pro):
    client.post(reverse("login_request"), data={"email": pro.email})

    assert mail.outbox[0].subject == "Votre lien de connexion à TechPourToutes"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_with_unknown_email_sends_nothing(client):
    response = client.post(reverse("login_request"), data={"email": "ghost@example.com"})

    assert response.status_code == 302
    assert response["Location"] == reverse("login_email_sent")
    assert mail.outbox == []


@pytest.mark.django_db
def test_login_request_post_with_back_carries_it_to_email_sent_page(client):
    response = client.post(
        reverse("login_request"), data={"email": "ghost@example.com", "back": "/mentorer/"}
    )

    assert response.status_code == 302
    assert response["Location"] == f"{reverse('login_email_sent')}?back=%2Fmentorer%2F"


@pytest.mark.django_db
def test_login_request_post_strips_external_back(client):
    response = client.post(
        reverse("login_request"),
        data={"email": "ghost@example.com", "back": "https://evil.com/x"},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("login_email_sent")


@pytest.mark.django_db
def test_login_request_post_from_email_sent_page_shows_confirmation_message(client):
    from django.conf import settings

    referer = f"{settings.SITE_URL}{reverse('login_email_sent')}"
    response = client.post(
        reverse("login_request"),
        data={"email": "ghost@example.com"},
        HTTP_REFERER=referer,
    )

    assert response.status_code == 302
    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Votre demande a bien été prise en compte." in m for m in stored)


@pytest.mark.django_db
def test_login_request_post_from_email_sent_page_with_back_shows_confirmation_message(client):
    from django.conf import settings

    referer = f"{settings.SITE_URL}{reverse('login_email_sent')}?back=%2Fmentorer%2F"
    response = client.post(
        reverse("login_request"),
        data={"email": "ghost@example.com"},
        HTTP_REFERER=referer,
    )

    assert response.status_code == 302
    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Votre demande a bien été prise en compte." in m for m in stored)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_with_inactive_user_sends_nothing(client, inactive_user):
    response = client.post(reverse("login_request"), data={"email": inactive_user.email})

    assert response.status_code == 302
    assert response["Location"] == reverse("login_email_sent")
    assert mail.outbox == []


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_embeds_safe_next_in_link(client, pro):
    client.post(
        reverse("login_request"),
        data={"email": pro.email, "next": "/mentorer/"},
    )

    html_body = mail.outbox[0].alternatives[0][0]
    assert "next=%2Fmentorer%2F" in html_body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_request_post_strips_external_next_from_link(client, pro):
    client.post(
        reverse("login_request"),
        data={"email": pro.email, "next": "https://evil.com/x"},
    )

    html_body = mail.outbox[0].alternatives[0][0]
    assert "next=" not in html_body


@pytest.mark.django_db
def test_sidebar_login_link_carries_current_page_as_back(client):
    from urllib.parse import quote

    response = client.get(reverse("mentor_landing"))

    assert response.status_code == 200
    expected_href = f"{reverse('login_request')}?back={quote(reverse('mentor_landing'))}"
    assert expected_href in response.content.decode()


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
def test_login_email_sent_close_button_points_to_back(client):
    session = client.session
    session["login_email"] = "alice@example.com"
    session.save()

    response = client.get(reverse("login_email_sent") + "?back=/mentorer/")

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
    other_user = User.objects.create_user(username="other@example.com", email="other@example.com")
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
def test_account_requires_login(client):
    response = client.get(reverse("account"))

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]
    assert "next=" in response["Location"]


@pytest.mark.django_db
def test_account_renders_when_authenticated(client, pro):
    client.force_login(pro)

    response = client.get(reverse("account"))

    assert response.status_code == 200


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

    user = User.objects.create_user(username="plain@example.com", email="plain@example.com")
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
def test_account_info_requires_login(client):
    response = client.get(reverse("account_info"))

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_account_info_returns_info_card(client, pro):
    client.force_login(pro)

    response = client.get(reverse("account_info"))

    assert response.status_code == 200
    assert "Alice" in response.content.decode()


@pytest.mark.django_db
def test_account_edit_requires_login(client):
    response = client.get(reverse("account_edit"))

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_account_edit_redirects_user_without_pro(client, db):
    from techpourtoutes.models import User

    user = User.objects.create_user(username="plain@example.com", email="plain@example.com")
    client.force_login(user)

    response = client.get(reverse("account_edit"))

    assert response.status_code == 302
    assert response["Location"] == reverse("account")


@pytest.mark.django_db
def test_account_edit_get_renders_form(client, pro):
    client.force_login(pro)

    response = client.get(reverse("account_edit"))

    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_account_edit_post_valid_saves_and_returns_info_card(client, pro):
    client.force_login(pro)

    response = client.post(
        reverse("account_edit"),
        data={
            "first_name": "Béatrice",
            "last_name": "Dupont",
            "phone": "+33698765432",
            "professional_situation": "working",
            "structure_name": "CNRS",
            "job_title": "Ingénieure",
            "postal_code": "69001",
        },
    )

    assert response.status_code == 200
    pro.refresh_from_db()
    assert pro.first_name == "Béatrice"
    assert pro.job_title == "Ingénieure"
    assert pro.postal_code == "69001"


@pytest.mark.django_db
def test_account_edit_post_invalid_returns_form_with_errors(client, pro):
    client.force_login(pro)

    response = client.post(
        reverse("account_edit"),
        data={"postal_code": "not-a-postcode"},
    )

    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_delete_account_get_not_allowed(client, pro):
    client.force_login(pro)

    response = client.get(reverse("delete_account"))

    assert response.status_code == 405


@pytest.mark.django_db
def test_delete_account_requires_login(client):
    response = client.post(reverse("delete_account"))

    assert response.status_code == 302
    assert reverse("login_request") in response["Location"]


@pytest.mark.django_db
def test_delete_account_with_invalid_form_rerenders_modal(client, pro):
    client.force_login(pro)

    response = client.post(reverse("delete_account"), data={})

    assert response.status_code == 200
    assert "form" in response.context
    assert response.context["form"].errors

    pro.refresh_from_db()
    assert pro.is_active


@patch("techpourtoutes.views.auth_views.SoftDeleteAccount")
@pytest.mark.django_db
def test_delete_account_post_valid_logs_out_redirects_and_shows_success_message(
    mock_service,
    client,
    pro,
):
    client.force_login(pro)

    mock_service.return_value.failure = False

    response = client.post(
        reverse("delete_account"),
        data={"confirm_delete": True},
    )

    mock_service.assert_called_once_with(user=pro)

    assert response.status_code == 200
    assert response["HX-Redirect"] == "/"

    assert client.session.get("_auth_user_id") is None

    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Votre compte a été supprimé." in m for m in stored)
