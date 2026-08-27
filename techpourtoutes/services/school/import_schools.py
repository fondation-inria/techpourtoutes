from techpourtoutes.utils.onisep import read_onisep_csv

from ..base import BaseService
from ..onisep_api.fetch_schools import FetchOnisepSchools
from .upsert_schools import UpsertSchools


class ImportSchools(BaseService):
    SCOPES = ("secondary", "higher_ed")
    SAMPLE_PREFIX = "schools"

    def perform(self, *, scope: str = "all", sample: bool = False) -> None:
        for single_scope in self._scopes_covered_by(scope):
            UpsertSchools(
                records=self._records_for(scope=single_scope, sample=sample), scope=single_scope
            )

    def _scopes_covered_by(self, scope):
        return self.SCOPES if scope == "all" else (scope,)

    def _records_for(self, *, scope, sample):
        return self._sample_records(scope) if sample else self._downloaded_records(scope)

    def _sample_records(self, scope):
        return read_onisep_csv(f"{self.SAMPLE_PREFIX}_{scope}_sample.csv")

    def _downloaded_records(self, scope):
        result = FetchOnisepSchools(scope=scope)
        if result.failure:
            self.fail_with_errors(result)
        return result.onisep_records
