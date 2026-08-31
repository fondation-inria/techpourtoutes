import json

import httpx

from .base import BaseClient

# The Carif-Oref apprenticeship catalogue, paginated and without an API key.
BASE_URL = "https://catalogue-apprentissage.intercariforef.org/api/v1"
PAGE_TIMEOUT = 60

# Left out, the API applies this very filter implicitly — but only as long as no `query` is
# passed at all. Stating it keeps the perimeter the day one is.
PUBLISHED = {"published": True, "catalogue_published": True}

# Whole records run past 20 MB a page and the response truncates mid-stream, so only the
# columns the mapper reads are asked for. `rncp_details` is a sub-object, hence the dots.
PROJECTION = {
    "onisep_url": 1,
    "niveau": 1,
    "duree": 1,
    "intitule_rco": 1,
    "rncp_details.nsf_code": 1,
    "rncp_details.type_certif": 1,
    "rncp_details.code_type_certif": 1,
    "etablissement_formateur_siret": 1,
    "etablissement_formateur_uai": 1,
    "etablissement_gestionnaire_siret": 1,
    "etablissement_gestionnaire_uai": 1,
}


class CarifOrefClient(BaseClient):
    def __init__(self):
        super().__init__(base_url=BASE_URL)

    def fetch_formations(self, *, page: int, limit: int) -> httpx.Response:
        return self.get(
            path="entity/formations",
            params={
                "query": json.dumps(PUBLISHED),
                "select": json.dumps(PROJECTION),
                "page": page,
                "limit": limit,
            },
            timeout=PAGE_TIMEOUT,
        )
