from celery import shared_task

from techpourtoutes.services.brevo_api.delete_contact import DeleteBrevoContact

from ._retry import RETRY_KWARGS, is_transient_status, retry_task_later


@shared_task(bind=True, **RETRY_KWARGS)
def delete_brevo_contact_task(self, ext_id: str, list_id: int):
    result = DeleteBrevoContact(ext_id=ext_id, list_id=list_id)
    if result.failure:
        message = ", ".join(result.errors)
        if is_transient_status(getattr(result, "status_code", None)):
            retry_task_later(message)
        raise RuntimeError(message)
