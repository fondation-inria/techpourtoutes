from celery import shared_task

from techpourtoutes.services.upsert_email_notification import UpsertEmailNotification

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def upsert_email_notification_task(self, email: str):
    result = UpsertEmailNotification(email=email)
    if result.failure:
        raise_failure(result)
