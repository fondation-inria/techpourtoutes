from unittest.mock import patch

import pytest

from techpourtoutes.models import Beneficiary
from techpourtoutes.services.beneficiary.join_discord_server import (
    ALREADY_LINKED_MESSAGE,
    JoinDiscordServer,
)

API_URL = "https://discord.com/api/v10"
MEMBER_URL = f"{API_URL}/guilds/42/members/1234"
REDIRECT_URI = "https://example.test/retour/"
REMOVAL_TASK = (
    "techpourtoutes.services.beneficiary.join_discord_server.remove_discord_guild_member_task"
)

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("discord_settings")]


@pytest.fixture
def discord_identity(httpx_mock):
    """Discord recognises the code as the one of the Discord account 1234."""
    httpx_mock.add_response(url=f"{API_URL}/oauth2/token", json={"access_token": "abc"})
    httpx_mock.add_response(url=f"{API_URL}/users/@me", json={"id": "1234"})


@pytest.fixture
def other_beneficiary(db):
    other = Beneficiary(
        username="lina@example.com",
        first_name="Lina",
        last_name="Moreau",
        email="lina@example.com",
        discord_user_id=1234,
    )
    other.save()
    return other


@pytest.mark.usefixtures("discord_identity")
def test_join_discord_server_adds_her_and_links_her_discord_account(httpx_mock, beneficiary):
    httpx_mock.add_response(url=MEMBER_URL, method="PUT", status_code=201)

    result = JoinDiscordServer(beneficiary=beneficiary, code="the-code", redirect_uri=REDIRECT_URI)

    assert result.success
    beneficiary.refresh_from_db()
    assert beneficiary.discord_user_id == 1234


@pytest.mark.usefixtures("discord_identity")
def test_join_discord_server_refuses_a_discord_account_linked_to_someone_else(
    beneficiary, other_beneficiary
):
    result = JoinDiscordServer(beneficiary=beneficiary, code="the-code", redirect_uri=REDIRECT_URI)

    assert result.errors == [ALREADY_LINKED_MESSAGE]
    beneficiary.refresh_from_db()
    assert beneficiary.discord_user_id is None


@pytest.mark.usefixtures("discord_identity")
def test_join_discord_server_leaves_her_unlinked_when_the_bot_cannot_add_her(
    httpx_mock, beneficiary
):
    httpx_mock.add_response(url=MEMBER_URL, method="PUT", status_code=403)

    result = JoinDiscordServer(beneficiary=beneficiary, code="the-code", redirect_uri=REDIRECT_URI)

    assert result.failure
    beneficiary.refresh_from_db()
    assert beneficiary.discord_user_id is None


def test_join_discord_server_fails_when_discord_refuses_the_code(httpx_mock, beneficiary):
    httpx_mock.add_response(url=f"{API_URL}/oauth2/token", status_code=400)

    result = JoinDiscordServer(beneficiary=beneficiary, code="stale", redirect_uri=REDIRECT_URI)

    assert result.failure


@pytest.mark.usefixtures("discord_identity")
def test_join_discord_server_removes_the_discord_account_she_linked_before(
    httpx_mock, beneficiary, django_capture_on_commit_callbacks
):
    beneficiary.discord_user_id = 999
    beneficiary.save()
    httpx_mock.add_response(url=MEMBER_URL, method="PUT", status_code=201)

    with patch(REMOVAL_TASK) as task, django_capture_on_commit_callbacks(execute=True):
        JoinDiscordServer(beneficiary=beneficiary, code="the-code", redirect_uri=REDIRECT_URI)

    task.delay.assert_called_once_with(999)


@pytest.mark.usefixtures("discord_identity")
def test_join_discord_server_keeps_the_account_she_links_again(
    httpx_mock, beneficiary, django_capture_on_commit_callbacks
):
    beneficiary.discord_user_id = 1234
    beneficiary.save()
    httpx_mock.add_response(url=MEMBER_URL, method="PUT", status_code=204)

    with patch(REMOVAL_TASK) as task, django_capture_on_commit_callbacks(execute=True):
        result = JoinDiscordServer(
            beneficiary=beneficiary, code="the-code", redirect_uri=REDIRECT_URI
        )

    assert result.success
    task.delay.assert_not_called()
