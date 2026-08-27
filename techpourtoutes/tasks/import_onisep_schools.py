from celery import shared_task

from techpourtoutes.services.school.import_schools import ImportSchools

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def import_onisep_schools_task(self, scope: str = "all", sample: bool = False):
    result = ImportSchools(scope=scope, sample=sample)
    if result.failure:
        raise_failure(result)
