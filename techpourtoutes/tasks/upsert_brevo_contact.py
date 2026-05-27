from celery import shared_task
from django.apps import apps

from techpourtoutes.services.brevo_api.upsert_contact import UpsertBrevoContact

from ._retry import RETRY_KWARGS, TransientError


@shared_task(bind=True, **RETRY_KWARGS)
def upsert_brevo_contact_task(self, instance_pk: str, model_label: str):
    instance = apps.get_model(model_label).objects.get(pk=instance_pk)
    result = UpsertBrevoContact(instance=instance)
    if result.failure:
        message = ", ".join(result.errors)
        if result.is_transient_failure:
            raise TransientError(message)
        raise RuntimeError(message)
