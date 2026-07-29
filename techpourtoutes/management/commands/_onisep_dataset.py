import csv
import re
from pathlib import Path

import httpx
from django.conf import settings
from django.core.management.base import CommandError

DATASET_URL = "https://api.opendata.onisep.fr/api/1.0/dataset/{dataset_id}/search"
LOGIN_URL = "https://api.opendata.onisep.fr/api/1.0/login"
PAGE_SIZE = 5000

FOR_AF_FIELDS = [
    "action_de_formation_af_identifiant_onisep",
    "formation_for_libelle",
    "for_url_et_id_onisep",
    "for_indexation_domaine_web_onisep",
    "for_type",
    "for_nature_du_certificat",
    "for_url_referentiel",
    "for_niveau_de_sortie",
    "af_duree_cycle_standard",
    "af_modalites_scolarite",
    "af_elements_denseignement",
    "af_cout_scolarite",
    "af_modalites_accueil",
    "af_page_web",
    "af_date_de_creation",
    "af_date_de_modification",
]

FIELDNAMES = ["uai", "school_name", "postal_code", "criterion", *FOR_AF_FIELDS]


def build_formation_row(record, *, uai, school_name, postal_code, criterion):
    row = {
        "uai": uai,
        "school_name": school_name,
        "postal_code": postal_code,
        "criterion": criterion,
    }
    for field in FOR_AF_FIELDS:
        row[field] = record.get(field, "")
    return row


def append_formation_rows(path, rows):
    if not rows:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerows(rows)


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
