from celery import shared_task

from techpourtoutes.services.contact.create_upcoming_feature_notification import (
    CreateUpcomingFeatureNotification,
)

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def create_upcoming_feature_notification_task(self, email: str):
    result = CreateUpcomingFeatureNotification(email=email)
    if result.failure:
        raise_failure(result)
