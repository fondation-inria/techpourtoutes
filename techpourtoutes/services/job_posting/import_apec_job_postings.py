import tempfile

from techpourtoutes.utils.apec import APEC_SAMPLE_PATH, read_apec_offers

from ..apec_sftp.fetch_job_postings import FetchApecJobPostings
from ..base import BaseService
from .upsert_apec_job_postings import UpsertApecJobPostings


class ImportApecJobPostings(BaseService):
    """Mirror the offers of the Apec export, or of the committed sample.

    The export is downloaded to disk and read from there one offer at a time, never held whole
    in memory. Nothing is written unless the whole file was read: the upsert deletes what it was
    not handed.
    """

    def perform(self, sample=False) -> None:
        if sample:
            self._upsert(APEC_SAMPLE_PATH)
            return
        with tempfile.TemporaryFile() as export:
            self._download(export)
            self._upsert(export)

    def _download(self, export) -> None:
        result = FetchApecJobPostings(file=export)
        if result.failure:
            self.fail_with_errors(result)
        export.seek(0)

    def _upsert(self, source) -> None:
        result = UpsertApecJobPostings(records=read_apec_offers(source))
        if result.failure:
            self.fail_with_errors(result)
