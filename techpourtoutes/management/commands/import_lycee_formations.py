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

        distinct_uais_added = set()
        for record in records:
            school_data = self._eligible_school_from_record(record)
            if school_data is None:
                continue
            uai, name, postal_code, level, is_digital = school_data
            EligibleSchool.objects.record(
                uai=uai,
                name=name,
                postal_code=postal_code,
                level=level,
                matches_digital_domain=is_digital,
            )
            distinct_uais_added.add(uai)

        self.stdout.write(
            self.style.SUCCESS(f"  {len(distinct_uais_added)} établissements importés.")
        )

    def _eligible_school_from_record(self, record):
        uai = record.get("ens_code_uai")
        if not uai:
            return None
        if not matches_any_acronym(record.get("formation_for_libelle", ""), CRITERIA_ACRONYMS):
            return None
        name = record["lieu_denseignement_ens_libelle"]
        postal_code = record.get("ens_code_postal", "")
        return uai, name, postal_code, EligibleSchool.EducationLevel.NON_SUP, True
