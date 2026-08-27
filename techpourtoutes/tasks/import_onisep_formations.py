from celery import shared_task

from techpourtoutes.services.formation.import_formations import ImportFormations

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def import_onisep_formations_task(self, sample: bool = False):
    result = ImportFormations(sample=sample)
    if result.failure:
        raise_failure(result)
