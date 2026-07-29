import re

import httpx
from django.conf import settings
from django.core.management.base import CommandError

DATASET_URL = "https://api.opendata.onisep.fr/api/1.0/dataset/{dataset_id}/search"
LOGIN_URL = "https://api.opendata.onisep.fr/api/1.0/login"
PAGE_SIZE = 5000


def get_auth_headers():
    response = httpx.post(
        LOGIN_URL,
        data={"email": settings.ONISEP_API_EMAIL, "password": settings.ONISEP_API_PASSWORD},
        timeout=30,
    )
    if not response.is_success:
        raise CommandError(f"Échec de l'authentification ONISEP (code {response.status_code}).")
    token = response.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "Application-ID": settings.ONISEP_APPLICATION_ID,
    }


def fetch_all_records(dataset_id, headers, extra_params=None):
    records = []
    offset = 0
    total = None
    while total is None or offset < total:
        response = httpx.get(
            DATASET_URL.format(dataset_id=dataset_id),
            params={"size": PAGE_SIZE, "from": offset, **(extra_params or {})},
            headers=headers,
            timeout=120,
        )
        if not response.is_success:
            raise CommandError(
                f"Échec de la récupération des données (code {response.status_code})."
            )
        payload = response.json()
        results = payload["results"]
        if not results:
            break
        records.extend(results)
        offset += len(results)
        total = payload["total"]
    return records


def matches_any_acronym(text, acronyms):
    return any(
        re.search(rf"\b{re.escape(acronym)}\b", text, re.IGNORECASE) for acronym in acronyms
    )
