import json

from techpourtoutes.utils.myfuture import MYFUTURE_SAMPLE_PATH

from ..base import BaseService
from ..myfuture_api.fetch_job_postings import FetchMyFutureJobPostings
from .upsert_myfuture_job_postings import UpsertMyFutureJobPostings


class ImportMyFutureJobPostings(BaseService):
    """Mirror the MyFuture offers of the sub-domains we follow, or those of the committed sample.

    Nothing is written unless every page came back: the upsert deletes what it was not handed.
    """

    def perform(self, sample=False) -> None:
        records = self._sample_records() if sample else self._downloaded_records()
        UpsertMyFutureJobPostings(records=records)

    def _sample_records(self):
        return json.loads(MYFUTURE_SAMPLE_PATH.read_text())

    def _downloaded_records(self):
        result = FetchMyFutureJobPostings()
        if result.failure:
            self.fail_with_errors(result)
        return result.myfuture_records
