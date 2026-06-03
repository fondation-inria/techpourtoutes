from celery import shared_task
from django.apps import apps

from techpourtoutes.services.n8n_api.notify_workshop_request import NotifyWorkshopRequest

from ._retry import RETRY_KWARGS, TransientError


@shared_task(bind=True, **RETRY_KWARGS)
def notify_workshop_request_task(self, pro_pk: str, ateliers: list[str], remark: str):
    pro = apps.get_model("techpourtoutes", "Pro").objects.get(pk=pro_pk)
    result = NotifyWorkshopRequest(pro=pro, ateliers=ateliers, remark=remark)
    if result.failure:
        message = ", ".join(result.errors)
        if result.is_transient_failure:
            raise TransientError(message)
        raise RuntimeError(message)
