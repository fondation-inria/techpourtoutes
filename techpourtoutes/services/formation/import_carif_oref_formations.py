from ..base import BaseService
from ..carif_oref_api.fetch_formations import FetchCarifOrefFormations
from .upsert_carif_oref_formations import UpsertCarifOrefFormations


class ImportCarifOrefFormations(BaseService):
    """Feed the apprenticeship formations from the Carif-Oref catalogue.

    Unlike the Onisep imports there is no committed sample to fall back on: the catalogue is
    only ever read over the network.
    """

    def perform(self) -> None:
        UpsertCarifOrefFormations(records=self._downloaded_records())

    def _downloaded_records(self):
        result = FetchCarifOrefFormations()
        if result.failure:
            self.fail_with_errors(result)
        return result.carif_oref_records
