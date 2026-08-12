from techpourtoutes.utils.onisep import read_onisep_csv

from ..base_api import BaseApiService
from ..onisep_api.fetch_formations import FetchOnisepFormations
from .upsert_formations import UpsertFormations


class ImportFormations(BaseApiService):
    SAMPLE = "formations_sample.csv"

    def perform(self, *, sample: bool = False) -> None:
        UpsertFormations(records=self._records(sample=sample))

    def _records(self, *, sample):
        return read_onisep_csv(self.SAMPLE) if sample else self._downloaded_records()

    def _downloaded_records(self):
        result = FetchOnisepFormations()
        if result.failure:
            self.fail_with_errors(result)
        return result.onisep_records
