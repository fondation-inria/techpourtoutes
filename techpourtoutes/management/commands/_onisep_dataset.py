import re

import httpx
from django.core.management.base import CommandError

DATASET_URL = "https://api.opendata.onisep.fr/api/1.0/dataset/{dataset_id}/search"
PAGE_SIZE = 1000


def fetch_all_records(dataset_id):
    records = []
    offset = 0
    while True:
        response = httpx.get(
            DATASET_URL.format(dataset_id=dataset_id),
            params={"size": PAGE_SIZE, "from": offset},
            timeout=120,
        )
        if not response.is_success:
            raise CommandError(
                f"Échec de la récupération des données (code {response.status_code})."
            )
        payload = response.json()
        results = payload["results"]
        records.extend(results)
        offset += len(results)
        if not results or offset >= payload["total"]:
            break
    return records


def matches_any_acronym(text, acronyms):
    return any(
        re.search(rf"\b{re.escape(acronym)}\b", text, re.IGNORECASE) for acronym in acronyms
    )
