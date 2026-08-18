from celery import shared_task

from techpourtoutes.models import Beneficiary
from techpourtoutes.services.beneficiary.create_mentoree import CreateMentoree

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def create_mentoree_task(self, beneficiary_pk: str):
    beneficiary = Beneficiary.objects.get(pk=beneficiary_pk)
    result = CreateMentoree(beneficiary=beneficiary)
    if result.failure:
        raise_failure(result)
