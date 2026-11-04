from techpourtoutes.utils.apec import APEC_SAMPLE_PATH, read_apec_xml

from ..apec_sftp.fetch_job_postings import FetchApecJobPostings
from ..base import BaseService
from .upsert_apec_job_postings import UpsertApecJobPostings


class ImportApecJobPostings(BaseService):
    """Mirror the offers of the Apec export, or of the committed sample.

    Nothing is written unless the whole file was read: the upsert deletes what it was not handed.
    """

    def perform(self, sample=False) -> None:
        records = self._sample_records() if sample else self._downloaded_records()
        result = UpsertApecJobPostings(records=records)
        if result.failure:
            self.fail_with_errors(result)

    def _sample_records(self):
        _, records = read_apec_xml(APEC_SAMPLE_PATH)
        return records

    def _downloaded_records(self):
        result = FetchApecJobPostings()
        if result.failure:
            self.fail_with_errors(result)
        return result.apec_records
