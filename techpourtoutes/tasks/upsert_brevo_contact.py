from celery import shared_task
from django.apps import apps

from techpourtoutes.services.contact.sync_brevo_contact import SyncBrevoContact

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def upsert_brevo_contact_task(self, instance_pk: str, model_label: str):
    instance = apps.get_model(model_label).objects.get(pk=instance_pk)
    result = SyncBrevoContact(instance=instance)
    if result.failure:
        raise_failure(result)
