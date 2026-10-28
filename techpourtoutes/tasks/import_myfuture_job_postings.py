from celery import shared_task

from techpourtoutes.services.job_posting.import_myfuture_job_postings import (
    ImportMyFutureJobPostings,
)

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def import_myfuture_job_postings_task(self):
    result = ImportMyFutureJobPostings()
    if result.failure:
        raise_failure(result)
