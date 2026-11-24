import pytest

from techpourtoutes.services.discord_api.identify_user import IdentifyDiscordUser

API_URL = "https://discord.com/api/v10"

pytestmark = pytest.mark.usefixtures("discord_settings")


def test_identify_user_trades_the_code_for_her_token_and_her_id(httpx_mock):
    httpx_mock.add_response(url=f"{API_URL}/oauth2/token", json={"access_token": "abc"})
    httpx_mock.add_response(url=f"{API_URL}/users/@me", json={"id": "1234"})

    result = IdentifyDiscordUser(code="the-code", redirect_uri="https://example.test/retour/")

    assert result.success
    assert result.access_token == "abc"
    assert result.user_id == 1234


def test_identify_user_fails_when_discord_refuses_the_code(httpx_mock):
    httpx_mock.add_response(url=f"{API_URL}/oauth2/token", status_code=400)

    result = IdentifyDiscordUser(code="stale", redirect_uri="https://example.test/retour/")

    assert result.failure
