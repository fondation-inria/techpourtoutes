import pytest

from techpourtoutes.services.discord_api.add_guild_member import AddDiscordGuildMember

MEMBER_URL = "https://discord.com/api/v10/guilds/42/members/1234"

pytestmark = pytest.mark.usefixtures("discord_settings")


@pytest.mark.parametrize("status_code", [201, 204], ids=["added", "already_member"])
def test_add_guild_member_succeeds_whether_she_was_added_or_already_there(httpx_mock, status_code):
    httpx_mock.add_response(url=MEMBER_URL, method="PUT", status_code=status_code)

    assert AddDiscordGuildMember(user_id=1234, access_token="abc").success


def test_add_guild_member_fails_when_the_bot_may_not_add_her(httpx_mock):
    httpx_mock.add_response(url=MEMBER_URL, method="PUT", status_code=403)

    assert AddDiscordGuildMember(user_id=1234, access_token="abc").failure
