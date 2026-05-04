import httpx
import pytest
from django.test import override_settings

JOBIRL_TEST_URL = "https://preprod.jobirl.com"
JOBIRL_TEST_API_KEY = "test-api-key-abc"


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_sends_correct_payload(httpx_mock, mentor):
    from api.services.jobirl import register_mentor_on_jobirl

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(url=register_url, status_code=200)

    register_mentor_on_jobirl(mentor)

    request = httpx_mock.get_request()
    assert request.method == "POST"
    assert f"Bearer Bearer: {JOBIRL_TEST_API_KEY}" in request.headers["Authorization"]
    body = request.content.decode()
    assert "alice%40example.com" in body or "alice@example.com" in body
    assert "Alice" in body
    assert "Martin" in body
    assert "jobirl_profil=pro" in body
    assert "mentorat_profil=mentor" in body
    assert "CTO" in body
    assert "75001" in body


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_raises_on_http_error(httpx_mock, mentor):
    from api.services.jobirl import JobirlAPIError, register_mentor_on_jobirl

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(url=register_url, status_code=401)

    with pytest.raises(JobirlAPIError):
        register_mentor_on_jobirl(mentor)


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_raises_on_network_error(httpx_mock, mentor):
    from api.services.jobirl import JobirlAPIError, register_mentor_on_jobirl

    httpx_mock.add_exception(httpx.RequestError("connection failed"))

    with pytest.raises(JobirlAPIError):
        register_mentor_on_jobirl(mentor)
