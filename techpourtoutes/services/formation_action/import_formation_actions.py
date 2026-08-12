from techpourtoutes.utils.onisep import onisep_id_from_url, read_onisep_csv

from ..base_api import BaseApiService
from ..onisep_api.fetch_formation_actions import FetchOnisepFormationActions
from .prune_formation_actions import PruneFormationActions
from .upsert_formation_actions import UpsertFormationActions


class ImportFormationActions(BaseApiService):
    """Feed the FormationAction table, from the committed samples or from the Onisep open data.
    Both ends must already be imported: an action whose formation or établissement is unknown
    is dropped by the upsert."""

    SCOPES = ("lycee", "superieur")
    SAMPLE_PREFIX = "formation_actions"

    def perform(self, *, scope: str = "all", sample: bool = False) -> None:
        active_onisep_ids = set()
        for single_scope in self._scopes_covered_by(scope):
            records = self._records_for(scope=single_scope, sample=sample)
            UpsertFormationActions(records=records)
            active_onisep_ids |= self._onisep_ids_in(records)
        if self._prunes(scope=scope, sample=sample):
            PruneFormationActions(active_onisep_ids=active_onisep_ids)

    def _onisep_ids_in(self, records):
        """The links a scope carries — what the prune must leave alone."""
        return {
            onisep_id_from_url(record.get("action_de_formation_af_identifiant_onisep"))
            for record in records
        }

    def _prunes(self, *, scope, sample):
        """Only a full download knows what the feed dropped: a sample and a single scope
        both describe a fraction of the table, and would take the rest down with them."""
        return scope == "all" and not sample

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
