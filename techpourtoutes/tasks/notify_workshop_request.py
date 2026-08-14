from celery import shared_task

from techpourtoutes.models import Pro
from techpourtoutes.services.n8n_api.notify_workshop_request import NotifyWorkshopRequest

from ._retry import RETRY_KWARGS, TransientError


@shared_task(bind=True, **RETRY_KWARGS)
def notify_workshop_request_task(
    self, pro_pk: str, ateliers: list[str], remark: str, structure_uai: str
):
    pro = Pro.objects.get(pk=pro_pk)
    result = NotifyWorkshopRequest(
        pro=pro, ateliers=ateliers, remark=remark, structure_uai=structure_uai
    )
    if result.failure:
        message = ", ".join(result.errors)
        if result.failed_with_transient_error():
            raise TransientError(message)
        raise RuntimeError(message)
