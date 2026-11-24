import pytest

from techpourtoutes.services.discord_api.remove_guild_member import RemoveDiscordGuildMember

MEMBER_URL = "https://discord.com/api/v10/guilds/42/members/1234"

pytestmark = pytest.mark.usefixtures("discord_settings")


def test_remove_guild_member_succeeds_when_she_is_removed(httpx_mock):
    httpx_mock.add_response(url=MEMBER_URL, method="DELETE", status_code=204)

    assert RemoveDiscordGuildMember(user_id=1234).success


def test_remove_guild_member_succeeds_when_she_already_left(httpx_mock):
    httpx_mock.add_response(url=MEMBER_URL, method="DELETE", status_code=404)

    assert RemoveDiscordGuildMember(user_id=1234).success


def test_remove_guild_member_fails_when_the_bot_may_not_remove_her(httpx_mock):
    httpx_mock.add_response(url=MEMBER_URL, method="DELETE", status_code=403)

    assert RemoveDiscordGuildMember(user_id=1234).failure
