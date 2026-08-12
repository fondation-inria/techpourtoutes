from celery import shared_task

from techpourtoutes.services.formation.import_formations import ImportFormations

from ._retry import RETRY_KWARGS, TransientError


@shared_task(bind=True, **RETRY_KWARGS)
def import_onisep_formations_task(self, sample: bool = False):
    result = ImportFormations(sample=sample)
    if result.failure:
        message = ", ".join(result.errors)
        if result.failed_with_transient_error():
            raise TransientError(message)
        raise RuntimeError(message)
