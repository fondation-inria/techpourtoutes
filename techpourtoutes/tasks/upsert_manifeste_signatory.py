from celery import shared_task

from techpourtoutes.services.brevo_api.upsert_manifeste_signatory import UpsertManifesteSignatory

from ._retry import RETRY_KWARGS, TransientError


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
        if result.is_transient_failure:
            raise TransientError(message)
        raise RuntimeError(message)
