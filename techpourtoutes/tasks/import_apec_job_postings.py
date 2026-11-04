from celery import shared_task

from techpourtoutes.services.job_posting.import_apec_job_postings import ImportApecJobPostings

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def import_apec_job_postings_task(self):
    result = ImportApecJobPostings()
    if result.failure:
        raise_failure(result)
