import json
import tempfile

from techpourtoutes.utils.myfuture import MYFUTURE_SAMPLE_PATH

from ..base import BaseService
from ..myfuture_api.fetch_job_postings import FetchMyFutureJobPostings
from .upsert_myfuture_job_postings import UpsertMyFutureJobPostings


class ImportMyFutureJobPostings(BaseService):
    """Mirror the MyFuture offers of the sub-domains we follow, or those of the committed sample.

    The pages are written to disk as they come, then read from there one offer at a time, never
    all held in memory. Nothing is written unless every page came back: the upsert deletes what
    it was not handed.
    """

    def perform(self, sample=False) -> None:
        if sample:
            UpsertMyFutureJobPostings(records=json.loads(MYFUTURE_SAMPLE_PATH.read_text()))
            return
        with tempfile.TemporaryFile("w+", encoding="utf-8") as file:
            self._download(file)
            UpsertMyFutureJobPostings(records=map(json.loads, file))

    def _download(self, file) -> None:
        result = FetchMyFutureJobPostings(file=file)
        if result.failure:
            self.fail_with_errors(result)
        file.seek(0)
