import base64

from django.test import override_settings

from techpourtoutes.clients.n8n import LatitudesN8nClient

WEBHOOK_URL = "https://n8n.example.test/webhook/atelier"
BASIC_AUTH_USER = "latitudes"
BASIC_AUTH_PASSWORD = "secret"


def _basic_auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


@override_settings(
    N8N_WORKSHOP_WEBHOOK_URL=WEBHOOK_URL,
    N8N_WORKSHOP_WEBHOOK_BASIC_AUTH_USER=BASIC_AUTH_USER,
    N8N_WORKSHOP_WEBHOOK_BASIC_AUTH_PASSWORD=BASIC_AUTH_PASSWORD,
)
def test_n8n_client_posts_workshop_payload_with_basic_auth_header(httpx_mock):
    httpx_mock.add_response(url=WEBHOOK_URL, status_code=200, json={"ok": True})

    response = LatitudesN8nClient().notify_workshop_request(payload={"hello": "world"})

    assert response.is_success
    request = httpx_mock.get_request()
    assert request.method == "POST"
    assert request.headers["Authorization"] == _basic_auth_header(
        BASIC_AUTH_USER, BASIC_AUTH_PASSWORD
    )
    assert request.headers["Content-Type"] == "application/json"
    assert request.content == b'{"hello":"world"}'


@override_settings(
    N8N_WORKSHOP_WEBHOOK_URL=WEBHOOK_URL,
    N8N_WORKSHOP_WEBHOOK_BASIC_AUTH_USER="",
    N8N_WORKSHOP_WEBHOOK_BASIC_AUTH_PASSWORD="",
)
def test_n8n_client_posts_without_auth_header_when_not_configured(httpx_mock):
    httpx_mock.add_response(url=WEBHOOK_URL, status_code=200, json={"ok": True})

    response = LatitudesN8nClient().notify_workshop_request(payload={"hello": "world"})

    assert response.is_success
    request = httpx_mock.get_request()
    assert "Authorization" not in request.headers
