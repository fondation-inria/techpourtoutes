import httpx
import pytest

from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.discord_api.base_service import (
    NETWORK_ERROR_MESSAGE,
    DiscordApiBaseService,
)

USER_URL = "https://discord.com/api/v10/users/@me"

pytestmark = pytest.mark.usefixtures("discord_settings")


class FetchMe(DiscordApiBaseService):
    def perform(self):
        self.response = self.request(method="fetch_current_user", access_token="abc")


def test_request_returns_the_response_on_success(httpx_mock):
    httpx_mock.add_response(url=USER_URL, json={"id": "1234"})

    result = FetchMe()

    assert result.success
    assert result.response.json() == {"id": "1234"}


def test_request_fails_transiently_when_discord_is_unreachable(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("boom"))

    result = FetchMe()

    assert result.errors == [NETWORK_ERROR_MESSAGE]
    assert result.error_kind is ErrorKind.TRANSIENT


def test_request_fails_transiently_when_rate_limited(httpx_mock):
    httpx_mock.add_response(url=USER_URL, status_code=429)

    result = FetchMe()

    assert result.error_kind is ErrorKind.TRANSIENT


def test_request_fails_permanently_on_a_client_error(httpx_mock):
    httpx_mock.add_response(url=USER_URL, status_code=401)

    result = FetchMe()

    assert result.failure
    assert result.error_kind is ErrorKind.PERMANENT
