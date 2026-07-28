from django.core.management.base import BaseCommand

from techpourtoutes.models import EligibleSchool

from ._onisep_dataset import fetch_all_records, matches_any_acronym

DATASET_ID = "605340ddc19a9"
ACCEPTED_STATUSES = {"public", "privé sous contrat"}
ACRONYMS = ["CIEL", "STMG", "STI2D", "TSI", "STL"]


class Command(BaseCommand):
    help = "Repère les lycées (bac CIEL / bac techno) pertinents depuis l'API ONISEP"

    def handle(self, *args, **options):
        matched = sum(self._record_if_matched(record) for record in fetch_all_records(DATASET_ID))
        self.stdout.write(self.style.SUCCESS(f"  {matched} établissements repérés."))

    def _record_if_matched(self, record):
        if not self._matches(record):
            return False
        EligibleSchool.objects.record(
            uai=record["ens_code_uai"],
            name=record["lieu_denseignement_ens_libelle"],
            postal_code=record.get("ens_code_postal", ""),
            level=EligibleSchool.EducationLevel.NON_SUP,
            matches_digital_domain=True,
        )
        return True

    def _matches(self, record):
        if record.get("ens_statut") not in ACCEPTED_STATUSES:
            return False
        return matches_any_acronym(record.get("formation_for_libelle", ""), ACRONYMS)
