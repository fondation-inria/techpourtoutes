import base64

import pytest

from techpourtoutes.clients.discord import DiscordClient

API_URL = "https://discord.com/api/v10"
MEMBER_URL = f"{API_URL}/guilds/42/members/1234"

pytestmark = pytest.mark.usefixtures("discord_settings")


def test_exchange_code_posts_the_code_with_the_app_credentials(httpx_mock):
    httpx_mock.add_response(url=f"{API_URL}/oauth2/token", json={"access_token": "abc"})

    DiscordClient().exchange_code(code="the-code", redirect_uri="https://example.test/retour/")

    request = httpx_mock.get_request()
    assert request.method == "POST"
    credentials = base64.b64encode(b"client-id:client-secret").decode()
    assert request.headers["Authorization"] == f"Basic {credentials}"
    assert request.content == (
        b"grant_type=authorization_code&code=the-code"
        b"&redirect_uri=https%3A%2F%2Fexample.test%2Fretour%2F"
    )


def test_fetch_current_user_reads_her_identity_with_her_token(httpx_mock):
    httpx_mock.add_response(url=f"{API_URL}/users/@me", json={"id": "1234"})

    DiscordClient().fetch_current_user(access_token="abc")

    assert httpx_mock.get_request().headers["Authorization"] == "Bearer abc"


def test_add_guild_member_puts_her_token_as_the_bot(httpx_mock):
    httpx_mock.add_response(url=MEMBER_URL, method="PUT", status_code=201)

    DiscordClient().add_guild_member(user_id=1234, access_token="abc")

    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bot bot-token"
    assert request.content == b'{"access_token":"abc"}'


def test_remove_guild_member_deletes_her_as_the_bot(httpx_mock):
    httpx_mock.add_response(url=MEMBER_URL, method="DELETE", status_code=204)

    DiscordClient().remove_guild_member(user_id=1234)

    assert httpx_mock.get_request().headers["Authorization"] == "Bot bot-token"


def test_bot_requests_carry_the_user_agent_discord_requires(httpx_mock):
    httpx_mock.add_response(url=MEMBER_URL, method="DELETE", status_code=204)

    DiscordClient().remove_guild_member(user_id=1234)

    assert httpx_mock.get_request().headers["User-Agent"].startswith("DiscordBot (")
