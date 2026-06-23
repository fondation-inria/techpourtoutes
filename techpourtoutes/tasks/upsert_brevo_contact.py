from celery import shared_task
from django.apps import apps

from techpourtoutes.services.sync_brevo_contact import SyncBrevoContact

from ._retry import RETRY_KWARGS, is_transient_status, retry_task_later


@shared_task(bind=True, **RETRY_KWARGS)
def upsert_brevo_contact_task(self, instance_pk: str, model_label: str):
    instance = apps.get_model(model_label).objects.get(pk=instance_pk)
    result = SyncBrevoContact(instance=instance)
    if result.failure:
        message = ", ".join(result.errors)
        if is_transient_status(getattr(result, "status_code", None)):
            retry_task_later(message)
        raise RuntimeError(message)
