from django.core.management.base import BaseCommand

from techpourtoutes.models import School, TrainingExperience


class Command(BaseCommand):
    help = "Repoint the parcours left on the merged schools onto their Onisep counterpart"

    def handle(self, *args, **options):
        remapped, detached = 0, 0
        for school in School.objects.legacy():
            target = self._onisep_counterpart(school)
            if target is None:
                detached += self._detach(school)
            else:
                remapped += TrainingExperience.objects.filter(school=school).update(school=target)
            school.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"  {remapped} formations rattachées, {detached} détachées sur le nom de "
                f"l'établissement."
            )
        )

    def _detach(self, school):
        """No counterpart to point at: the name the parcours displayed becomes its free text,
        which is what lets the placeholder go away without amputating anything."""
        return TrainingExperience.objects.filter(school=school).update(
            school=None, out_of_scope_school_name=school.display_label
        )

    def _onisep_counterpart(self, school):
        """UAI first, then SIRET. A shared UAI is resolved by lowest Onisep id, so a rerun
        on another database lands on the same établissement."""
        candidates = School.objects.imported()
        for field in ("uai", "siret"):
            value = getattr(school, field)
            if not value:
                continue
            match = candidates.filter(**{field: value}).order_by("onisep_id").first()
            if match is not None:
                return match
        return None
