from techpourtoutes.utils.onisep import read_onisep_csv

from ..base import BaseService
from ..onisep_api.fetch_formation_actions import FetchOnisepFormationActions
from .upsert_formation_actions import UpsertFormationActions


class ImportFormationActions(BaseService):
    """Feed the FormationAction table, from the committed samples or from the Onisep open data.
    Both ends must already be imported: an action whose formation or établissement is unknown
    is dropped by the upsert."""

    SCOPES = ("lycee", "superieur")
    SAMPLE_PREFIX = "formation_actions"

    def perform(self, *, scope: str = "all", sample: bool = False) -> None:
        for single_scope in self._scopes_covered_by(scope):
            UpsertFormationActions(
                records=self._records_for(scope=single_scope, sample=sample),
                scope=single_scope,
            )

    def _scopes_covered_by(self, scope):
        return self.SCOPES if scope == "all" else (scope,)

    def _records_for(self, *, scope, sample):
        return self._sample_records(scope) if sample else self._downloaded_records(scope)

    def _sample_records(self, scope):
        return read_onisep_csv(f"{self.SAMPLE_PREFIX}_{scope}_sample.csv")

    def _downloaded_records(self, scope):
        result = FetchOnisepFormationActions(scope=scope)
        if result.failure:
            self.fail_with_errors(result)
        return result.onisep_records
