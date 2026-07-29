from django.conf import settings
from django.core.management.base import BaseCommand

from techpourtoutes.models import EligibleSchool

from ._onisep_dataset import (
    append_formation_rows,
    build_formation_row,
    fetch_all_records,
    get_auth_headers,
    matches_any_acronym,
)

DATASET_ID = "605340ddc19a9"
ACCEPTED_STATUSES = {"public", "privé sous contrat"}
CRITERIA_ACRONYMS = ["CIEL", "STMG", "STI2D", "TSI", "STL"]

DEFAULT_ALL_PATH = settings.BASE_DIR / "data" / "exports" / "formations_all.csv"
DEFAULT_DIGITAL_PATH = settings.BASE_DIR / "data" / "exports" / "formations_digital.csv"


class Command(BaseCommand):
    help = "Repère les lycées (bac CIEL / bac techno) pertinents depuis l'API ONISEP"

    def add_arguments(self, parser):
        parser.add_argument("--all-path", default=str(DEFAULT_ALL_PATH))
        parser.add_argument("--digital-path", default=str(DEFAULT_DIGITAL_PATH))

    def handle(self, *args, **options):
        headers = get_auth_headers()
        records = [
            record
            for status in ACCEPTED_STATUSES
            for record in fetch_all_records(
                DATASET_ID, headers, extra_params={"facet.ens_statut": status}
            )
        ]

        all_rows = []
        distinct_uais_added = set()
        for record in records:
            school_data = self._eligible_school_from_record(record)
            if school_data is None:
                continue
            uai, name, postal_code, level, is_digital = school_data
            all_rows.append(
                build_formation_row(
                    record, uai=uai, school_name=name, postal_code=postal_code, criterion="lycee"
                )
            )
            EligibleSchool.objects.record(
                uai=uai,
                name=name,
                postal_code=postal_code,
                level=level,
                matches_digital_domain=is_digital,
            )
            distinct_uais_added.add(uai)

        append_formation_rows(options["all_path"], all_rows)
        append_formation_rows(options["digital_path"], all_rows)
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
