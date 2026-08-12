from celery import shared_task

from techpourtoutes.services.school.import_schools import ImportSchools

from ._retry import RETRY_KWARGS, TransientError


@shared_task(bind=True, **RETRY_KWARGS)
def import_onisep_schools_task(self, scope: str = "all", sample: bool = False):
    result = ImportSchools(scope=scope, sample=sample)
    if result.failure:
        message = ", ".join(result.errors)
        if result.failed_with_transient_error():
            raise TransientError(message)
        raise RuntimeError(message)
