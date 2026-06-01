from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
def test_mentor_landing_get(client):
    assert client.get(reverse("mentor_landing")).status_code == 200


@pytest.mark.django_db
def test_mentor_landing_post_valid_redirects(client, valid_pro_data, mock_create_mentor):
    response = client.post(reverse("mentor_landing"), data=valid_pro_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
def test_mentor_landing_post_invalid_rerenders_with_errors(client, valid_pro_data):
    response = client.post(reverse("mentor_landing"), data={**valid_pro_data, "email": ""})
    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_mentor_landing_post_duplicate_email_shows_error(client, valid_pro_data):
    from techpourtoutes.forms import ProForm

    form = ProForm(data=valid_pro_data)
    assert form.is_valid()
    form.save()

    response = client.post(reverse("mentor_landing"), data=valid_pro_data)
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_coalition_welcome_get(client):
    assert client.get(reverse("coalition_welcome")).status_code == 200


@pytest.mark.django_db
def test_mentor_landing_post_shows_error_on_create_mentor_failure(client, valid_pro_data):
    failed = MagicMock(success=False, failure=True, errors=["erreur de synchronisation"])
    with patch(
        "techpourtoutes.views.coalition_views.CreateMentor",
        return_value=failed,
    ):
        response = client.post(reverse("mentor_landing"), data=valid_pro_data)

    assert response.status_code == 200
    assert "erreur" in response.content.decode().lower()


@pytest.mark.django_db
def test_internships_landing_get(client):
    assert client.get(reverse("internships_landing")).status_code == 200


@pytest.mark.django_db
def test_work_ambassador_landing_get(client):
    assert client.get(reverse("work_ambassador_landing")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_work_ambassador_landing_post_valid_redirects(client, valid_pro_data):
    response = client.post(reverse("work_ambassador_landing"), data=valid_pro_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("coalition_welcome")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_work_ambassador_landing_post_valid_persists_engagement(client, valid_pro_data):
    from techpourtoutes.models import Pro

    client.post(reverse("work_ambassador_landing"), data=valid_pro_data)

    pro = Pro.objects.get(email=valid_pro_data["email"])
    assert "work_ambassador" in pro.engagements


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
)
def test_work_ambassador_landing_post_valid_sends_welcome_and_new_pro_emails(
    client, valid_pro_data
):
    from django.core import mail

    client.post(reverse("work_ambassador_landing"), data=valid_pro_data)

    assert len(mail.outbox) == 2
    recipients = {tuple(msg.to) for msg in mail.outbox}
    assert (valid_pro_data["email"],) in recipients
    assert ("ambassador@example.com",) in recipients


@pytest.mark.django_db
def test_work_ambassador_landing_post_invalid_rerenders_with_errors(client, valid_pro_data):
    response = client.post(
        reverse("work_ambassador_landing"), data={**valid_pro_data, "email": ""}
    )
    assert response.status_code == 200
    assert response.context["form"].errors
