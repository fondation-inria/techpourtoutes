from unittest.mock import MagicMock, patch

import httpx
import pytest
from django.test import override_settings

from techpourtoutes.services.n8n_api.notify_workshop_request import NotifyWorkshopRequest

WEBHOOK_URL = "https://n8n.example.test/webhook/atelier"


def _response(status_code):
    response = MagicMock()
    response.is_success = 200 <= status_code < 300
    response.status_code = status_code
    return response


@pytest.fixture
def pro(db):
    from techpourtoutes.models import Pro

    pro = Pro(
        username="manon@example.com",
        civility=Pro.Civility.MADAME,
        first_name="Manon",
        last_name="Desbordes",
        email="manon@example.com",
        professional_situation=Pro.ProfessionalSituation.WORKING,
        job_title="Enseignante",
        structure_name="Lycée Voltaire",
        structure_id="0750001A",
        postal_code="75011",
    )
    pro.save()
    return pro


@pytest.mark.django_db
@override_settings(N8N_WORKSHOP_WEBHOOK_URL=WEBHOOK_URL)
def test_notify_workshop_request_posts_expected_payload(pro):
    with patch("techpourtoutes.services.n8n_api.base_service.httpx.post") as mock_post:
        mock_post.return_value = _response(200)
        result = NotifyWorkshopRequest(
            pro=pro, ateliers=["future_of_tech", "future_of_ia"], remark="Merci !"
        )

    assert result.success
    args, kwargs = mock_post.call_args
    assert args[0] == WEBHOOK_URL
    payload = kwargs["json"]
    assert payload["type_atelier"] == ["future_of_tech", "future_of_ia"]
    assert payload["prenom"] == "Manon"
    assert payload["nom"] == "Desbordes"
    assert payload["email"] == "manon@example.com"
    assert payload["etablissement"] == "Lycée Voltaire"
    assert payload["identifiant_etablissement"] == "0750001A"
    assert payload["code_postal"] == "75011"
    assert payload["fonction"] == "Enseignante"
    assert payload["remarque"] == "Merci !"
    assert "timestamp" in payload


@pytest.mark.django_db
@override_settings(N8N_WORKSHOP_WEBHOOK_URL=WEBHOOK_URL)
def test_notify_workshop_request_fails_on_server_error_marked_transient(pro):
    with patch("techpourtoutes.services.n8n_api.base_service.httpx.post") as mock_post:
        mock_post.return_value = _response(503)
        result = NotifyWorkshopRequest(pro=pro, ateliers=["future_of_tech"], remark="")

    assert result.failure
    assert result.is_transient_failure


@pytest.mark.django_db
@override_settings(N8N_WORKSHOP_WEBHOOK_URL=WEBHOOK_URL)
def test_notify_workshop_request_client_error_not_transient(pro):
    with patch("techpourtoutes.services.n8n_api.base_service.httpx.post") as mock_post:
        mock_post.return_value = _response(400)
        result = NotifyWorkshopRequest(pro=pro, ateliers=["future_of_tech"], remark="")

    assert result.failure
    assert not result.is_transient_failure


@pytest.mark.django_db
@override_settings(N8N_WORKSHOP_WEBHOOK_URL=WEBHOOK_URL)
def test_notify_workshop_request_network_error_marked_transient(pro):
    with patch(
        "techpourtoutes.services.n8n_api.base_service.httpx.post",
        side_effect=httpx.ConnectError("boom"),
    ):
        result = NotifyWorkshopRequest(pro=pro, ateliers=["future_of_tech"], remark="")

    assert result.failure
    assert result.is_transient_failure
