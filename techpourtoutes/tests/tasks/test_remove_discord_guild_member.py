from unittest.mock import MagicMock, patch

import pytest

from techpourtoutes.tasks._retry import TransientError
from techpourtoutes.tasks.remove_discord_guild_member import remove_discord_guild_member_task

SERVICE = "techpourtoutes.tasks.remove_discord_guild_member.RemoveDiscordGuildMember"


def test_remove_discord_guild_member_task_runs_service():
    with patch(SERVICE) as mock_service:
        mock_service.return_value = MagicMock(failure=False, errors=[])

        remove_discord_guild_member_task(1234)

        mock_service.assert_called_once_with(user_id=1234)


def test_remove_discord_guild_member_task_raises_runtime_error_on_permanent_failure():
    with patch(SERVICE) as mock_service:
        mock_service.return_value = MagicMock(
            failure=True, errors=["nope"], failed_with_transient_error=False
        )

        with pytest.raises(RuntimeError, match="nope"):
            remove_discord_guild_member_task(1234)


def test_remove_discord_guild_member_task_raises_transient_error_on_transient_failure():
    with patch(SERVICE) as mock_service:
        mock_service.return_value = MagicMock(
            failure=True, errors=["nope"], failed_with_transient_error=True
        )

        with pytest.raises(TransientError, match="nope"):
            remove_discord_guild_member_task(1234)
