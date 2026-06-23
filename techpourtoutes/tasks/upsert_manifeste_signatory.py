from celery import shared_task

from techpourtoutes.services.upsert_manifeste_signatory import UpsertManifesteSignatory

from ._retry import RETRY_KWARGS, is_transient_status, retry_task_later


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
        if is_transient_status(getattr(result, "status_code", None)):
            retry_task_later(message)
        raise RuntimeError(message)
