from django.core.management.base import BaseCommand

from techpourtoutes.models import EligibleSchool, HigherEdSchool

from ._onisep_dataset import fetch_all_records, get_auth_headers, matches_any_acronym

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


class Command(BaseCommand):
    help = "Repère les établissements du supérieur (CPGE + informatique/réseau) via l'API ONISEP"

    def handle(self, *args, **options):
        self._sync_higher_ed_schools()

        known_uais = set(EligibleSchool.objects.values_list("uai", flat=True))
        headers = get_auth_headers()
        records = fetch_all_records(DATASET_ID, headers)

        touched_uais = set()
        for record in records:
            classified = self._classify(record, known_uais)
            if classified is None:
                continue
            uai, name, postal_code, level, is_digital = classified
            EligibleSchool.objects.record(
                uai=uai,
                name=name,
                postal_code=postal_code,
                level=level,
                matches_digital_domain=is_digital,
            )
            touched_uais.add(uai)

        self.stdout.write(self.style.SUCCESS(f"  {len(touched_uais)} établissements importés."))

    def _sync_higher_ed_schools(self):
        for school in HigherEdSchool.objects.exclude(uai=""):
            EligibleSchool.objects.record(
                uai=school.uai,
                name=school.display_label,
                postal_code="",
                level=EligibleSchool.EducationLevel.SUP,
                matches_digital_domain=False,
            )

    def _classify(self, record, known_uais):
        uai = record.get("ens_code_uai")
        if not uai:
            return None
        libelle = record.get("formation_for_libelle", "")
        name = record.get("lieu_denseignement_ens_libelle", "")
        postal_code = record.get("ens_code_postal", "")

        if (
            record.get("for_type") == CPGE_FOR_TYPE
            and record.get("ens_statut") in ACCEPTED_STATUSES
            and matches_any_acronym(libelle, CPGE_ACRONYMS)
        ):
            return uai, name, postal_code, EligibleSchool.EducationLevel.BOTH, True

        is_lycee = self._is_hosted_at_lycee(record)
        is_digital = self._is_digital(record)

        if uai not in known_uais:
            if not (is_lycee and is_digital and record.get("ens_statut") in ACCEPTED_STATUSES):
                return None
            return uai, name, postal_code, EligibleSchool.EducationLevel.BOTH, True

        level = (
            EligibleSchool.EducationLevel.BOTH if is_lycee else EligibleSchool.EducationLevel.SUP
        )
        return uai, name, postal_code, level, is_digital

    def _is_hosted_at_lycee(self, record):
        return "lycée" in record.get("lieu_denseignement_ens_libelle", "").lower()

    def _is_digital(self, record):
        domain = record.get("for_indexation_domaine_web_onisep", "").lower()
        if any(keyword in domain for keyword in DIGITAL_KEYWORDS):
            return True
        libelle = record.get("formation_for_libelle", "").lower()
        return any(keyword in libelle for keyword in DIGITAL_KEYWORDS)
