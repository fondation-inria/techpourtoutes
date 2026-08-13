from celery import shared_task

from techpourtoutes.services.upsert_email_notification import UpsertEmailNotification

from ._retry import RETRY_KWARGS, is_transient_status, retry_task_later


@shared_task(bind=True, **RETRY_KWARGS)
def upsert_email_notification_task(self, email: str):
    result = UpsertEmailNotification(email=email)
    if result.failure:
        message = ", ".join(result.errors)
        if is_transient_status(getattr(result, "status_code", None)):
            retry_task_later(message)
        raise RuntimeError(message)
