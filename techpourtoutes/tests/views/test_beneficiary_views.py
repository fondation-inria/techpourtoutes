from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse

BIENTOT_DISPONIBLE_URL = "/bientot-disponible/"


@pytest.mark.django_db
def test_bientot_disponible_get_returns_200(client):
    assert client.get(BIENTOT_DISPONIBLE_URL).status_code == 200


@pytest.mark.django_db
@override_settings(BREVO_SYNC_ENABLED=True)
def test_bientot_disponible_post_valid_pushes_brevo_contact_and_redirects(client):
    with patch(
        "techpourtoutes.views.beneficiary_views.upsert_email_notification_task"
    ) as mock_task:
        response = client.post(BIENTOT_DISPONIBLE_URL, data={"email": "hedy@example.com"})

    assert response.status_code == 302
    assert response.url == BIENTOT_DISPONIBLE_URL
    mock_task.delay.assert_called_once_with(email="hedy@example.com")


@pytest.mark.django_db
@override_settings(BREVO_SYNC_ENABLED=False)
def test_bientot_disponible_post_skips_task_when_sync_disabled(client):
    with patch(
        "techpourtoutes.views.beneficiary_views.upsert_email_notification_task"
    ) as mock_task:
        response = client.post(BIENTOT_DISPONIBLE_URL, data={"email": "hedy@example.com"})

    assert response.status_code == 302
    mock_task.delay.assert_not_called()


@pytest.mark.django_db
def test_bientot_disponible_post_invalid_rerenders_with_errors(client):
    response = client.post(BIENTOT_DISPONIBLE_URL, data={"email": "not-an-email"})
    assert response.status_code == 200
    assert response.context["form"].errors
    messages = list(response.context["messages"])
    assert len(messages) > 0


FIND_MENTOR_LANDING_URL = "/trouver-une-mentore/"


@pytest.mark.django_db
def test_find_mentor_landing_cta_for_anonymous_user(client):
    response = client.get(FIND_MENTOR_LANDING_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/inscription/?wants_mentor=1"
    assert response.context["cta_label"] == "S'inscrire au mentorat"
    assert response.context["cta_disabled"] is False


@pytest.mark.django_db
def test_find_mentor_landing_cta_for_connected_unregistered_beneficiary(client, beneficiary):
    client.force_login(beneficiary)

    response = client.get(FIND_MENTOR_LANDING_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/devenir-mentoree/"
    assert response.context["cta_label"] == "S'inscrire au mentorat"
    assert response.context["cta_disabled"] is False


@pytest.mark.django_db
def test_find_mentor_landing_cta_for_connected_registered_beneficiary(client, beneficiary):
    beneficiary.jobirl_user_id = 42
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(FIND_MENTOR_LANDING_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == reverse("login_to_jobirl")
    assert response.context["cta_label"] == "Rejoindre mon espace mentorat"
    assert response.context["cta_disabled"] is False


@pytest.mark.django_db
def test_find_mentor_landing_cta_disabled_for_registration_pending_jobirl_account(
    client, beneficiary
):
    beneficiary.legal_representative_email = "parent.durand@example.com"
    beneficiary.save()
    client.force_login(beneficiary)

    response = client.get(FIND_MENTOR_LANDING_URL)

    assert response.status_code == 200
    assert response.context["cta_label"] == "Rejoindre mon espace mentorat"
    assert response.context["cta_disabled"] is True


@pytest.mark.django_db
def test_find_mentor_landing_cta_for_connected_non_beneficiary_points_to_add_mentoring(
    client, pro
):
    client.force_login(pro)

    response = client.get(FIND_MENTOR_LANDING_URL)

    assert response.status_code == 200
    assert response.context["cta_href"] == "/devenir-mentoree/"
    assert response.context["cta_label"] == "S'inscrire au mentorat"
    assert response.context["cta_disabled"] is False
