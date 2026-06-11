import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import School
from techpourtoutes.text import strip_accents

DATASET_URL = (
    "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "fr-en-annuaire-education/exports/json"
)


class Command(BaseCommand):
    help = "Import établissements (hors écoles) from data.education.gouv.fr into the School table"

    def handle(self, *args, **options):
        records = self._fetch_records()
        # The source can list an établissement more than once; de-duplicate by identifier
        # (keeping the last occurrence) so a single bulk insert never updates a row twice.
        schools_by_id = {
            record["identifiant_de_l_etablissement"]: School(
                identifier=record["identifiant_de_l_etablissement"],
                name=record["nom_etablissement"],
                name_normalized=strip_accents(record["nom_etablissement"]),
                postal_code=record.get("code_postal") or "",
            )
            for record in records
            if record.get("identifiant_de_l_etablissement") and record.get("nom_etablissement")
        }
        schools = list(schools_by_id.values())
        School.objects.bulk_create(
            schools,
            update_conflicts=True,
            unique_fields=["identifier"],
            update_fields=["name", "name_normalized", "postal_code"],
            batch_size=1000,
        )
        self.stdout.write(self.style.SUCCESS(f"  {len(schools)} établissements importés."))

    def _fetch_records(self):
        response = httpx.get(
            DATASET_URL,
            params={
                "select": "identifiant_de_l_etablissement,nom_etablissement,code_postal",
                "where": 'type_etablissement != "Ecole"',
            },
            headers={"Authorization": f"Apikey {settings.HUWISE_API_KEY}"},
            timeout=120,
        )
        if not response.is_success:
            raise CommandError(
                f"Échec de la récupération des données (code {response.status_code})."
            )
        return response.json()
