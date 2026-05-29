import httpx
import pytest
from django.test import override_settings

JOBIRL_TEST_URL = "https://preprod.jobirl.com"
JOBIRL_TEST_API_KEY = "test-api-key-abc"


@pytest.mark.django_db
@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_refresh_access_token_sends_correct_payload_and_exposes_token(httpx_mock, pro):
    from techpourtoutes.services.jobirl_api.refresh_access_token import RefreshAccessToken

    pro.jobirl_user_id = 12345
    pro.jobirl_user_token = "old-token"
    pro.save()

    refresh_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_refresh_access_token"
    httpx_mock.add_response(
        url=refresh_url,
        status_code=200,
        json={"response": "success", "datas": {"token": "new-token-abc"}},
    )

    result = RefreshAccessToken(pro=pro)

    assert result.success
    assert result.token == "new-token-abc"
    request = httpx_mock.get_request()
    assert request.method == "POST"
    body = request.content.decode()
    assert "iduser=12345" in body
    assert "token=old-token" in body


@pytest.mark.django_db
@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_refresh_access_token_updates_mentor_token_in_db(httpx_mock, pro):
    from techpourtoutes.services.jobirl_api.refresh_access_token import RefreshAccessToken

    pro.jobirl_user_id = 12345
    pro.jobirl_user_token = "old-token"
    pro.save()

    refresh_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_refresh_access_token"
    httpx_mock.add_response(
        url=refresh_url,
        status_code=200,
        json={"response": "success", "datas": {"token": "new-token-abc"}},
    )

    RefreshAccessToken(pro=pro)

    pro.refresh_from_db()
    assert pro.jobirl_user_token == "new-token-abc"


@pytest.mark.django_db
@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_refresh_access_token_fails_on_http_error(httpx_mock, pro):
    from techpourtoutes.services.jobirl_api.refresh_access_token import RefreshAccessToken

    refresh_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_refresh_access_token"
    httpx_mock.add_response(url=refresh_url, status_code=401)

    result = RefreshAccessToken(pro=pro)

    assert result.failure
    assert result.errors


@pytest.mark.django_db
@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_refresh_access_token_fails_on_network_error(httpx_mock, pro):
    from techpourtoutes.services.jobirl_api.refresh_access_token import RefreshAccessToken

    httpx_mock.add_exception(httpx.RequestError("connection failed"))

    result = RefreshAccessToken(pro=pro)

    assert result.failure
    assert result.errors


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_sends_correct_payload_and_exposes_ids(httpx_mock, pro):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(
        url=register_url,
        status_code=200,
        json={"response": "success", "datas": {"id": 287565, "token": "tpt_abc"}},
    )

    result = RegisterMentorOnJobirl(pro=pro)

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
    assert "Chercheuse" in body
    assert "75001" in body
    assert "civilite=Madame" in body


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_fails_on_http_error(httpx_mock, pro):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(url=register_url, status_code=401)

    result = RegisterMentorOnJobirl(pro=pro)

    assert result.failure
    assert result.errors


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_includes_api_message_on_4xx(httpx_mock, pro):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(
        url=register_url,
        status_code=400,
        json={
            "response": "error",
            "datas": {"message": "NAME MISSING, VILLE INVALIDE"},
        },
    )

    result = RegisterMentorOnJobirl(pro=pro)

    assert result.failure
    joined = " ".join(result.errors)
    assert "400" in joined
    assert "NAME MISSING, VILLE INVALIDE" in joined


@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_register_mentor_on_jobirl_fails_on_network_error(httpx_mock, pro):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    httpx_mock.add_exception(httpx.RequestError("connection failed"))

    result = RegisterMentorOnJobirl(pro=pro)

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
    httpx_mock, pro, professional_situation, expected_situation_pro
):
    from techpourtoutes.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

    pro.professional_situation = professional_situation
    pro.save()

    register_url = f"{JOBIRL_TEST_URL}/techpourtoutes/api/user_register"
    httpx_mock.add_response(
        url=register_url,
        status_code=200,
        json={"response": "success", "datas": {"id": 1, "token": "t"}},
    )

    RegisterMentorOnJobirl(pro=pro)

    body = httpx_mock.get_request().content.decode()
    assert f"situation_pro={expected_situation_pro}" in body
