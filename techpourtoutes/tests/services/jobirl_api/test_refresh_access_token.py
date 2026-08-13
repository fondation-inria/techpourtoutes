import httpx
import pytest
from django.test import override_settings

JOBIRL_TEST_URL = "https://preprod.jobirl.com"
JOBIRL_TEST_API_KEY = "test-api-key-abc"


@pytest.mark.django_db
@override_settings(JOBIRL_URL=JOBIRL_TEST_URL, JOBIRL_API_KEY=JOBIRL_TEST_API_KEY)
def test_refresh_access_token_sends_correct_data_and_exposes_token(httpx_mock, pro):
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
