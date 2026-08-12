from django.core.management.base import BaseCommand

from techpourtoutes.models import School, TrainingExperience


class Command(BaseCommand):
    help = "Repoint the parcours left on the merged schools onto their Onisep counterpart"

    def handle(self, *args, **options):
        remapped, unresolved = 0, 0
        for school in School.objects.legacy():
            target = self._onisep_counterpart(school)
            if target is None:
                unresolved += 1
                continue
            remapped += TrainingExperience.objects.filter(school=school).update(school=target)
            # Only the placeholders we could repoint go away. Deleting the others would blank
            # their parcours for good, where keeping them lets a later run resolve them.
            school.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"  {remapped} formations rattachées, {unresolved} établissements non retrouvés."
            )
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
