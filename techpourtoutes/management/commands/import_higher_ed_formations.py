from django.conf import settings
from django.core.management.base import BaseCommand

from techpourtoutes.models import EligibleSchool, HigherEdSchool

from ._onisep_dataset import (
    append_formation_rows,
    build_formation_row,
    fetch_all_records,
    get_auth_headers,
    matches_any_acronym,
)

DATASET_ID = "605344579a7d7"
ACCEPTED_STATUSES = {"public", "privé sous contrat"}

CPGE_FOR_TYPE = "prépa scientifique et technologique"
CPGE_ACRONYMS = [
    "MP2I",
    "MPSI",
    "PCSI",
    "MP",
    "PC",
    "PSI",
    "PTSI",
    "PT",
    "MPI",
    "BCPST",
    "TSI",
    "TPC",
]
DIGITAL_KEYWORDS = ["informatique", "réseau"]

DEFAULT_ALL_PATH = settings.BASE_DIR / "data" / "exports" / "formations_all.csv"
DEFAULT_DIGITAL_PATH = settings.BASE_DIR / "data" / "exports" / "formations_digital.csv"


class Command(BaseCommand):
    help = "Repère les établissements du supérieur (CPGE + informatique/réseau) via l'API ONISEP"

    def add_arguments(self, parser):
        parser.add_argument("--all-path", default=str(DEFAULT_ALL_PATH))
        parser.add_argument("--digital-path", default=str(DEFAULT_DIGITAL_PATH))

    def handle(self, *args, **options):
        self._sync_higher_ed_schools()

        known_uais = set(EligibleSchool.objects.values_list("uai", flat=True))
        headers = get_auth_headers()
        records = fetch_all_records(DATASET_ID, headers)

        all_rows = []
        digital_rows = []
        distinct_uais_added = set()
        for record in records:
            school_data = self._eligible_school_from_record(record, known_uais)
            if school_data is None:
                continue
            uai, name, postal_code, level, is_digital, criterion = school_data
            row = build_formation_row(
                record, uai=uai, school_name=name, postal_code=postal_code, criterion=criterion
            )
            all_rows.append(row)
            if is_digital:
                digital_rows.append(row)
            EligibleSchool.objects.record(
                uai=uai,
                name=name,
                postal_code=postal_code,
                level=level,
                matches_digital_domain=is_digital,
            )
            distinct_uais_added.add(uai)

        append_formation_rows(options["all_path"], all_rows)
        append_formation_rows(options["digital_path"], digital_rows)
        self.stdout.write(
            self.style.SUCCESS(f"  {len(distinct_uais_added)} établissements importés.")
        )

    def _sync_higher_ed_schools(self):
        for school in HigherEdSchool.objects.exclude(uai=""):
            for uai in school.uai.split(";"):
                EligibleSchool.objects.record(
                    uai=uai,
                    name=school.display_label,
                    postal_code="",
                    level=EligibleSchool.EducationLevel.SUP,
                    matches_digital_domain=False,
                )

    def _eligible_school_from_record(self, record, known_uais):
        uai = record.get("ens_code_uai")
        if not uai:
            return None
        label = record.get("formation_for_libelle", "")
        name = record.get("lieu_denseignement_ens_libelle", "")
        postal_code = record.get("ens_code_postal", "")

        if (
            record.get("for_type") == CPGE_FOR_TYPE
            and record.get("ens_statut") in ACCEPTED_STATUSES
            and matches_any_acronym(label, CPGE_ACRONYMS)
        ):
            return uai, name, postal_code, EligibleSchool.EducationLevel.BOTH, True, "cpge"

        is_lycee = self._is_hosted_at_lycee(record)
        is_digital = self._is_digital(record)

        if uai not in known_uais:
            if not (is_lycee and is_digital and record.get("ens_statut") in ACCEPTED_STATUSES):
                return None
            return uai, name, postal_code, EligibleSchool.EducationLevel.BOTH, True, "lycee_sup"

        level = (
            EligibleSchool.EducationLevel.BOTH if is_lycee else EligibleSchool.EducationLevel.SUP
        )
        criterion = "lycee_sup" if is_lycee else "higher_ed"
        return uai, name, postal_code, level, is_digital, criterion

    def _is_hosted_at_lycee(self, record):
        return "lycée" in record.get("lieu_denseignement_ens_libelle", "").lower()

    def _is_digital(self, record):
        domain = record.get("for_indexation_domaine_web_onisep", "").lower()
        if any(keyword in domain for keyword in DIGITAL_KEYWORDS):
            return True
        label = record.get("formation_for_libelle", "").lower()
        return any(keyword in label for keyword in DIGITAL_KEYWORDS)
