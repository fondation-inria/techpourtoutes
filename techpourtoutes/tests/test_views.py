from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_mentor_landing_get(client):
    assert client.get(reverse("mentor_landing")).status_code == 200


@pytest.mark.django_db
def test_mentor_landing_post_valid_redirects(client, valid_pro_data, mock_create_mentor):
    response = client.post(reverse("mentor_landing"), data=valid_pro_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("coallition_welcome")


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
def test_coallition_welcome_get(client):
    assert client.get(reverse("coallition_welcome")).status_code == 200


@pytest.mark.django_db
def test_mentor_landing_post_shows_error_on_create_mentor_failure(client, valid_pro_data):
    failed = MagicMock(success=False, failure=True, errors=["erreur de synchronisation"])
    with patch(
        "techpourtoutes.views.coallition_views.CreateMentor",
        return_value=failed,
    ):
        response = client.post(reverse("mentor_landing"), data=valid_pro_data)

    assert response.status_code == 200
    assert "erreur" in response.content.decode().lower()
