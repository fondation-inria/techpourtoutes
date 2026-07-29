from django.core.management.base import BaseCommand

from techpourtoutes.models import EligibleSchool

from ._onisep_dataset import fetch_all_records, get_auth_headers, matches_any_acronym

DATASET_ID = "605340ddc19a9"
ACCEPTED_STATUSES = {"public", "privé sous contrat"}
CRITERIA_ACRONYMS = ["CIEL", "STMG", "STI2D", "TSI", "STL"]


class Command(BaseCommand):
    help = "Repère les lycées (bac CIEL / bac techno) pertinents depuis l'API ONISEP"

    def handle(self, *args, **options):
        headers = get_auth_headers()
        records = [
            record
            for status in ACCEPTED_STATUSES
            for record in fetch_all_records(
                DATASET_ID, headers, extra_params={"facet.ens_statut": status}
            )
        ]

        count = 0
        for record in records:
            if not self._is_matched(record):
                continue
            uai = record.get("ens_code_uai")
            if not uai:
                continue
            EligibleSchool.objects.record(
                uai=uai,
                name=record["lieu_denseignement_ens_libelle"],
                postal_code=record.get("ens_code_postal", ""),
                level=EligibleSchool.EducationLevel.NON_SUP,
                matches_digital_domain=True,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"  {count} établissements importés."))

    def _is_matched(self, record):
        if record.get("ens_statut") not in ACCEPTED_STATUSES:
            return False
        return matches_any_acronym(record.get("formation_for_libelle", ""), CRITERIA_ACRONYMS)
