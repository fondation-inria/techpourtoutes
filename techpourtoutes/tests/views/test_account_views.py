from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.messages import get_messages
from django.core import mail
from django.urls import reverse

from techpourtoutes.models import Beneficiary


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
def test_account_info_displays_beneficiary_birth_date(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(reverse("account_info"))

    assert response.status_code == 200
    assert "15/03/2008" in response.content.decode()


@pytest.mark.django_db
def test_account_edit_get_renders_form_for_beneficiary(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(reverse("account_edit"))

    assert response.status_code == 200
    assert response.context["form"].initial["first_name"] == "Jade"
    # <input type="date"> ignores the localised fr format, so the value must be ISO.
    assert 'value="2008-03-15"' in response.content.decode()


@pytest.mark.django_db
def test_account_edit_post_valid_saves_beneficiary_and_returns_info_card(client, beneficiary):
    client.force_login(beneficiary)

    response = client.post(
        reverse("account_edit"),
        data={"first_name": "Léa", "last_name": "Petit", "birth_date": "2008-03-15"},
    )

    assert response.status_code == 200
    beneficiary.refresh_from_db()
    assert beneficiary.first_name == "Léa"


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


@patch("techpourtoutes.views.account_views.SoftDeleteAccount")
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
    assert any("Le compte a bien été supprimé." in m for m in stored)


@patch("techpourtoutes.views.account_views.SoftDeleteAccount")
@pytest.mark.django_db
def test_delete_account_post_valid_calls_service_with_beneficiary_instance(
    mock_service,
    client,
    beneficiary,
):
    client.force_login(beneficiary)

    mock_service.return_value.failure = False

    client.post(
        reverse("delete_account"),
        data={"confirm_delete": True},
    )

    called_user = mock_service.call_args.kwargs["user"]
    assert isinstance(called_user, Beneficiary)
    assert called_user.pk == beneficiary.pk


def _token_from_redirect(response):
    return parse_qs(urlparse(response.url).query)["token"][0]


def _token_from_hx_redirect(response):
    return parse_qs(urlparse(response["HX-Redirect"]).query)["token"][0]


@pytest.mark.django_db
def test_email_change_get_renders_inline_form(client, pro):
    client.force_login(pro)

    response = client.get(reverse("email_change"))

    assert response.status_code == 200
    assert "form" in response.context
    assert 'id="account-email-section"' in response.content.decode()


@pytest.mark.django_db
def test_account_email_get_renders_display_section(client, pro):
    client.force_login(pro)

    response = client.get(reverse("account_email"))

    assert response.status_code == 200
    assert "Changer mon adresse mail" in response.content.decode()


@patch("techpourtoutes.models.user.generate_numeric_code", return_value="123456")
@pytest.mark.django_db
def test_email_change_post_valid_mails_current_and_hx_redirects(_code, client, pro):
    client.force_login(pro)

    response = client.post(reverse("email_change"), data={"email": "new@example.com"})

    assert response.status_code == 200
    assert reverse("email_change_verify") in response["HX-Redirect"]
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [pro.email]


@pytest.mark.django_db
def test_email_change_post_invalid_rerenders_with_errors(client, pro):
    client.force_login(pro)

    response = client.post(reverse("email_change"), data={"email": pro.email})

    assert response.status_code == 200
    assert response.context["form"].errors
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_email_change_verify_get_shows_masked_recipient(client, pro):
    client.force_login(pro)
    token = pro.issue_email_change_token("new@example.com", "current")

    response = client.get(reverse("email_change_verify"), data={"token": token})

    assert response.status_code == 200
    assert "a***e@example.com" in response.content.decode()


@pytest.mark.django_db
def test_email_change_verify_bad_token_redirects_to_account(client, pro):
    client.force_login(pro)

    response = client.get(reverse("email_change_verify"), data={"token": "garbage"})

    assert response.status_code == 302
    assert response.url == reverse("account")


@patch("techpourtoutes.models.user.generate_numeric_code", return_value="123456")
@pytest.mark.django_db
def test_email_change_verify_wrong_code_rerenders(_code, client, pro):
    client.force_login(pro)
    pro.set_email_change_code()
    token = pro.issue_email_change_token("new@example.com", "current")

    response = client.post(reverse("email_change_verify"), data={"token": token, "code": "000000"})

    assert response.status_code == 200
    pro.refresh_from_db()
    assert pro.email_change_attempts == 1


@patch("techpourtoutes.models.user.generate_numeric_code", return_value="123456")
@pytest.mark.django_db
def test_email_change_full_flow_updates_email(_code, client, pro):
    client.force_login(pro)

    start = client.post(reverse("email_change"), data={"email": "new@example.com"})
    current_token = _token_from_hx_redirect(start)

    verify_current = client.post(
        reverse("email_change_verify"), data={"token": current_token, "code": "123456"}
    )
    assert verify_current.status_code == 302
    assert mail.outbox[-1].to == ["new@example.com"]
    new_token = _token_from_redirect(verify_current)

    verify_new = client.post(
        reverse("email_change_verify"), data={"token": new_token, "code": "123456"}
    )

    assert verify_new.status_code == 302
    assert verify_new.url == reverse("account")
    pro.refresh_from_db()
    assert pro.email == "new@example.com"
    assert pro.username == "new@example.com"
    stored = [str(m) for m in get_messages(verify_new.wsgi_request)]
    assert any("adresse mail a bien été modifiée" in m for m in stored)


@patch("techpourtoutes.models.user.generate_numeric_code", return_value="123456")
@pytest.mark.django_db
def test_email_change_resend_remails(_code, client, pro):
    client.force_login(pro)
    pro.set_email_change_code()
    token = pro.issue_email_change_token("new@example.com", "current")

    response = client.post(reverse("email_change_resend"), data={"token": token})

    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [pro.email]
    stored = [str(m) for m in get_messages(response.wsgi_request)]
    assert "Un nouveau code a été envoyé par mail." in stored


@pytest.mark.django_db
def test_account_page_shows_communication_checkbox_checked_when_synced(client, pro):
    client.force_login(pro)
    content = client.get(reverse("account")).content.decode()
    assert "Je veux recevoir ponctuellement des nouvelles de TechPourToutes" in content
    assert "account-communication-card" in content
    assert "checked" in content


@pytest.mark.django_db
def test_account_communication_opt_in_enables_brevo_sync(client, pro):
    pro.brevo_sync_enabled = False
    pro.save()
    client.force_login(pro)

    response = client.post(reverse("account_communication"), data={"newsletter_consent": "on"})

    assert response.status_code == 200
    pro.refresh_from_db()
    assert pro.brevo_sync_enabled is True


@pytest.mark.django_db
def test_account_communication_opt_out_disables_brevo_sync(client, pro):
    client.force_login(pro)

    response = client.post(reverse("account_communication"), data={})

    assert response.status_code == 200
    pro.refresh_from_db()
    assert pro.brevo_sync_enabled is False


@pytest.mark.django_db(transaction=True)
def test_account_communication_opt_out_dispatches_delete(client, pro):
    client.force_login(pro)

    with patch("techpourtoutes.signals.delete_brevo_contact_task") as delete_task:
        client.post(reverse("account_communication"), data={})

    delete_task.delay.assert_called_once_with(ext_id=str(pro.pk), list_id=42)


@pytest.mark.django_db
def test_account_communication_works_for_beneficiary(client, beneficiary):
    client.force_login(beneficiary)

    response = client.post(reverse("account_communication"), data={"newsletter_consent": "on"})

    assert response.status_code == 200
    beneficiary.refresh_from_db()
    assert beneficiary.brevo_sync_enabled is True
