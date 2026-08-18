from celery import shared_task

from techpourtoutes.models import Pro
from techpourtoutes.services.jobirl_api.register_user import RegisterUserOnJobirl

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def create_mentor_task(self, pro_pk: str):
    """Catches up the Jobirl half of CreateMentor — the pro is already saved and notified."""
    pro = Pro.objects.get(pk=pro_pk)
    result = RegisterUserOnJobirl(user=pro, is_pro=True)
    if result.failure:
        raise_failure(result)
    pro.jobirl_user_id = result.user_id
    pro.jobirl_user_token = result.token
    pro.save()
