from celery import shared_task

from techpourtoutes.services.discord_api.remove_guild_member import RemoveDiscordGuildMember

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def remove_discord_guild_member_task(self, discord_user_id: int):
    result = RemoveDiscordGuildMember(user_id=discord_user_id)
    if result.failure:
        raise_failure(result)
