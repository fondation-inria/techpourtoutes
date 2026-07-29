import json
from collections import defaultdict

import httpx
from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import EligibleSchool, HigherEdSchool

FORMATIONS_URL = "https://catalogue-apprentissage.intercariforef.org/api/v1/entity/formations"
PAGE_SIZE = 1000
UAI_BATCH_SIZE = 30

UAI_FIELDS = [
    "etablissement_formateur_uai",
    "etablissement_gestionnaire_uai",
    "etablissement_lieu_formation_uai",
]

DIGITAL_KEYWORDS = ["informatique", "réseau"]


class Command(BaseCommand):
    help = (
        "Repère les formations en apprentissage des établissements du supérieur connus "
        "via le Catalogue Apprentissage (intercariforef)"
    )

    def handle(self, *args, **options):
        schools_by_uai = self._schools_by_uai()
        records = self._fetch_records(schools_by_uai)

        distinct_uais_added = set()

        for record in records:
            is_digital = self._is_digital(record)
            record_uais = {record.get(field) for field in UAI_FIELDS} & schools_by_uai.keys()
            for uai in record_uais:
                for school in schools_by_uai[uai]:
                    EligibleSchool.objects.record(
                        uai=uai,
                        name=school.display_label,
                        postal_code=record.get("code_postal") or "",
                        level=EligibleSchool.EducationLevel.SUP,
                        matches_digital_domain=False,
                        matches_digital_apprenticeship=is_digital,
                    )
                    distinct_uais_added.add(uai)

        self.stdout.write(
            self.style.SUCCESS(f"  {len(distinct_uais_added)} établissements mis à jour.")
        )

    def _schools_by_uai(self):
        schools_by_uai = defaultdict(list)
        for school in HigherEdSchool.objects.exclude(uai=""):
            for uai in school.uai.split(";"):
                schools_by_uai[uai].append(school)
        return schools_by_uai

    def _fetch_records(self, schools_by_uai):
        uais = list(schools_by_uai)
        records_by_id = {}
        for i in range(0, len(uais), UAI_BATCH_SIZE):
            batch = uais[i : i + UAI_BATCH_SIZE]
            for record in self._fetch_formations_for_uais(batch):
                records_by_id[record["id"]] = record
        return records_by_id.values()

    def _fetch_formations_for_uais(self, uais):
        query = {"$or": [{field: uai} for uai in uais for field in UAI_FIELDS]}
        records = []
        page = 1
        total_pages = 1
        while page <= total_pages:
            response = httpx.get(
                FORMATIONS_URL,
                params={"query": json.dumps(query), "page": page, "limit": PAGE_SIZE},
                timeout=120,
            )
            if not response.is_success:
                raise CommandError(
                    "Échec de la récupération des formations en apprentissage "
                    f"(code {response.status_code})."
                )
            payload = response.json()
            records.extend(payload["formations"])
            total_pages = payload["pagination"]["nombre_de_page"]
            page += 1
        return records

    def _is_digital(self, record):
        domain = record.get("onisep_domaine_sousdomaine") or ""
        discipline = record.get("onisep_discipline") or ""
        label = record.get("intitule_long") or ""
        haystack = f"{domain} {discipline} {label}".lower()
        return any(keyword in haystack for keyword in DIGITAL_KEYWORDS)
