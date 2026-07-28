from django.core.management.base import BaseCommand

from techpourtoutes.models import EligibleSchool, HigherEdSchool

from ._onisep_dataset import fetch_all_records, matches_any_acronym

DATASET_ID = "605344579a7d7"

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
DIGITAL_KEYWORDS = ["numérique", "informatique"]


class Command(BaseCommand):
    help = (
        "Repère les établissements du supérieur (CPGE + numérique/informatique) via l'API ONISEP"
    )

    def handle(self, *args, **options):
        self._sync_higher_ed_schools()
        known_uais = set(EligibleSchool.objects.values_list("uai", flat=True))
        matched = sum(
            self._record_if_matched(record, known_uais) for record in fetch_all_records(DATASET_ID)
        )
        self.stdout.write(self.style.SUCCESS(f"  {matched} établissements mis à jour."))

    def _sync_higher_ed_schools(self):
        for school in HigherEdSchool.objects.exclude(uai=""):
            EligibleSchool.objects.record(
                uai=school.uai,
                name=school.display_label,
                postal_code="",
                level=EligibleSchool.EducationLevel.SUP,
                matches_digital_domain=False,
            )

    def _record_if_matched(self, record, known_uais):
        uai = record.get("ens_code_uai")
        libelle = record.get("formation_for_libelle", "")

        if record.get("for_type") == CPGE_FOR_TYPE and matches_any_acronym(libelle, CPGE_ACRONYMS):
            self._record(record, uai, EligibleSchool.EducationLevel.BOTH)
            return True

        if uai not in known_uais or not self._is_digital(record):
            return False

        self._record(record, uai, EligibleSchool.EducationLevel.SUP)
        return True

    def _record(self, record, uai, level):
        EligibleSchool.objects.record(
            uai=uai,
            name=record["lieu_denseignement_ens_libelle"],
            postal_code=record.get("ens_code_postal", ""),
            level=level,
            matches_digital_domain=True,
        )

    def _is_digital(self, record):
        domain = record.get("for_indexation_domaine_web_onisep", "").lower()
        if any(keyword in domain for keyword in DIGITAL_KEYWORDS):
            return True
        libelle = record.get("formation_for_libelle", "").lower()
        return any(keyword in libelle for keyword in DIGITAL_KEYWORDS)
