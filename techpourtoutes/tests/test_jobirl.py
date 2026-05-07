import httpx
import pytest
from django.test import override_settings

JOBIRL_TEST_URL = "https://preprod.jobirl.com"
JOBIRL_TEST_API_KEY = "test-api-key-abc"


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_sends_correct_payload_and_exposes_ids(httpx_mock, mentor):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(
        url=register_url,
        status_code=200,
        json={"response": "success", "datas": {"id": 287565, "token": "tpt_abc"}},
    )

    result = RegisterMentorOnJobirl(mentor=mentor)

    assert result.success
    assert result.user_id == 287565
    assert result.token == "tpt_abc"
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
def test_register_mentor_on_jobirl_fails_on_http_error(httpx_mock, mentor):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(url=register_url, status_code=401)

    result = RegisterMentorOnJobirl(mentor=mentor)

    assert result.failure
    assert result.errors


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_includes_api_message_on_4xx(httpx_mock, mentor):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(
        url=register_url,
        status_code=400,
        json={
            "response": "error",
            "datas": {"message": "ADRESSE MISSING, VILLE INVALIDE"},
        },
    )

    result = RegisterMentorOnJobirl(mentor=mentor)

    assert result.failure
    joined = " ".join(result.errors)
    assert "400" in joined
    assert "ADRESSE MISSING, VILLE INVALIDE" in joined


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_fails_on_network_error(httpx_mock, mentor):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    httpx_mock.add_exception(httpx.RequestError("connection failed"))

    result = RegisterMentorOnJobirl(mentor=mentor)

    assert result.failure
    assert result.errors


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
@pytest.mark.parametrize(
    "professional_situation,expected_situation_pro",
    [
        ("working", "actif"),
        ("student", "actif"),
        ("retired", "retraite"),
        ("jobless", "chomeur"),
    ],
)
def test_register_mentor_maps_professional_situation(
    httpx_mock, mentor, professional_situation, expected_situation_pro
):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    mentor.professional_situation = professional_situation
    mentor.save()

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(
        url=register_url,
        status_code=200,
        json={"response": "success", "datas": {"id": 1, "token": "t"}},
    )

    RegisterMentorOnJobirl(mentor=mentor)

    body = httpx_mock.get_request().content.decode()
    assert f"situation_pro={expected_situation_pro}" in body
