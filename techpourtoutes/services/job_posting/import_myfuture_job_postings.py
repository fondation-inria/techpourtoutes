from ..base import BaseService
from ..myfuture_api.fetch_job_postings import FetchMyFutureJobPostings
from .upsert_myfuture_job_postings import UpsertMyFutureJobPostings


class ImportMyFutureJobPostings(BaseService):
    """Mirror the MyFuture offers of the sub-domains we follow.

    Nothing is written unless every page came back: the upsert deletes what it was not handed.
    """

    def perform(self, sample=False) -> None:
        UpsertMyFutureJobPostings(records=self._downloaded_records(sample=sample))

    def _downloaded_records(self, *, sample):
        result = FetchMyFutureJobPostings(sample=sample)
        if result.failure:
            self.fail_with_errors(result)
        return result.myfuture_records
