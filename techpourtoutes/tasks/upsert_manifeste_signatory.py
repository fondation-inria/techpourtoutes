from celery import shared_task

from techpourtoutes.services.contact.upsert_manifeste_signatory import UpsertManifesteSignatory

from ._retry import RETRY_KWARGS, retry_task_later


@shared_task(bind=True, **RETRY_KWARGS)
def upsert_manifeste_signatory_task(
    self, first_name: str, last_name: str, email: str, structure_name: str
):
    result = UpsertManifesteSignatory(
        first_name=first_name,
        last_name=last_name,
        email=email,
        structure_name=structure_name,
    )
    if result.failure:
        message = ", ".join(result.errors)
        if result.failed_with_transient_error():
            retry_task_later(message)
        raise RuntimeError(message)
