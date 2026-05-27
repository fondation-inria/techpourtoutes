from celery import shared_task

from techpourtoutes.services.brevo_api.delete_contact import DeleteBrevoContact

from ._retry import RETRY_KWARGS


@shared_task(bind=True, **RETRY_KWARGS)
def delete_brevo_contact_task(self, ext_id: str, list_id: int):
    result = DeleteBrevoContact(ext_id=ext_id, list_id=list_id)
    if result.failure:
        raise RuntimeError(", ".join(result.errors))
