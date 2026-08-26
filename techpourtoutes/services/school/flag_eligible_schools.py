from django.db.models import Q

from techpourtoutes.models import School

from ..base import BaseService

PUBLIC_STATUSES = ["public", "privé sous contrat"]
TECHNOLOGICAL_BAC_CODES = ["STMG", "STI2D", "STL"]
CPGE_CODES = [
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
LYCEE_TYPES = ["lycée professionnel", "lycée général, technologique ou polyvalent"]


class FlagEligibleSchools(BaseService):
    """Mark the schools matching at least one of 5 criteria: bac pro CIEL, bac
    techno STMG/STI2D/STL, scientific CPGE, training ambassador schools, and lycées teaching
    a computer-science-related formation. Recomputed from scratch on every call."""

    def perform(self) -> None:
        eligible_ids = self._eligible_school_ids()

        School.objects.exclude(id__in=eligible_ids).update(eligible=False)
        School.objects.filter(id__in=eligible_ids).update(eligible=True)

    def _eligible_school_ids(self):
        eligible_schools = (
            self._bac_pro_ciel_schools()
            | self._technological_schools()
            | self._cpge_schools()
            | self._training_ambassador_eligible_schools()
            | self._computer_science_lycees()
        )
        return eligible_schools.values_list("id", flat=True).distinct()

    def _bac_pro_ciel_schools(self):
        return School.objects.filter(
            status__in=PUBLIC_STATUSES,
            formations__acronym="CIEL",
        )

    def _technological_schools(self):
        name_matches = Q()
        for code in TECHNOLOGICAL_BAC_CODES:
            name_matches |= Q(formations__name__icontains=code)

        return School.objects.filter(
            name_matches,
            status__in=PUBLIC_STATUSES,
            formations__type_name="baccalauréat technologique",
        )

    def _cpge_schools(self):
        name_matches = Q()
        for code in CPGE_CODES:
            name_matches |= Q(formations__name__icontains=code)

        return School.objects.filter(
            name_matches,
            status__in=PUBLIC_STATUSES,
            formations__type_acronym="CPGE",
            formations__type_name="classe préparatoire scientifique et technologique",
        )

    def _training_ambassador_eligible_schools(self):
        return School.objects.filter(training_ambassador_eligible=True)

    def _computer_science_lycees(self):
        computer_science_matches = Q(formations__domain__icontains="informatique") | Q(
            formations__name__icontains="administrateur réseau"
        )

        return School.objects.filter(
            computer_science_matches,
            type__in=LYCEE_TYPES,
            status__in=PUBLIC_STATUSES,
        )
