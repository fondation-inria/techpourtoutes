from unittest.mock import MagicMock, patch

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
def test_mentor_landing_get(client):
    assert client.get(reverse("mentor_landing")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_mentor_landing_post_valid_redirects(
    client, valid_mentor_data, mock_register_mentor_on_jobirl
):
    response = client.post(reverse("mentor_landing"), data=valid_mentor_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("mentor_success")


@pytest.mark.django_db
def test_mentor_landing_post_invalid_rerenders_with_errors(client, valid_mentor_data):
    response = client.post(reverse("mentor_landing"), data={**valid_mentor_data, "email": ""})
    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_mentor_landing_post_duplicate_email_shows_error(client, valid_mentor_data):
    from techpourtoutes.forms import MentorForm

    form = MentorForm(data=valid_mentor_data)
    assert form.is_valid()
    form.save()

    response = client.post(reverse("mentor_landing"), data=valid_mentor_data)
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_mentor_success_get(client):
    assert client.get(reverse("mentor_success")).status_code == 200


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_mentor_landing_post_sends_welcome_email(
    client, valid_mentor_data, mock_register_mentor_on_jobirl
):
    client.post(reverse("mentor_landing"), data=valid_mentor_data)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [valid_mentor_data["email"]]
    assert "Bienvenue" in mail.outbox[0].subject
    assert mail.outbox[0].alternatives


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_mentor_landing_post_calls_jobirl_api(
    client, valid_mentor_data, mock_register_mentor_on_jobirl
):
    from techpourtoutes.models import Mentor

    client.post(reverse("mentor_landing"), data=valid_mentor_data)

    mentor = Mentor.objects.get(email=valid_mentor_data["email"])
    mock_register_mentor_on_jobirl.assert_called_once_with(mentor=mentor)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_mentor_landing_post_saves_jobirl_ids_on_mentor(
    client, valid_mentor_data, mock_register_mentor_on_jobirl
):
    from techpourtoutes.models import Mentor

    client.post(reverse("mentor_landing"), data=valid_mentor_data)

    mentor = Mentor.objects.get(email=valid_mentor_data["email"])
    assert mentor.jobirl_user_id == 287565
    assert mentor.jobirl_user_token == "tpt_abc"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_mentor_landing_post_shows_error_on_jobirl_failure(client, valid_mentor_data):
    from techpourtoutes.models import Mentor

    failed = MagicMock(success=False, failure=True, errors=["erreur de synchronisation"])
    with patch(
        "techpourtoutes.views.coallition_views.RegisterMentorOnJobirl",
        return_value=failed,
    ):
        response = client.post(reverse("mentor_landing"), data=valid_mentor_data)

    assert response.status_code == 200
    assert not Mentor.objects.filter(email=valid_mentor_data["email"]).exists()
    assert len(mail.outbox) == 0
    assert "erreur" in response.content.decode().lower()
