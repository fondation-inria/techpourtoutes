from django.core.management.base import BaseCommand

from techpourtoutes.models import Formation, TrainingExperience


class Command(BaseCommand):
    help = "Point the parcours still holding a free-text filière at their Onisep formation"

    def handle(self, *args, **options):
        pending = TrainingExperience.objects.filter(formation__isnull=True).exclude(course="")
        linked = 0
        for experience in pending:
            experience.formation = self._formation_for(experience)
            if experience.formation is not None:
                experience.save(update_fields=["formation"])
                linked += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  {linked} formations rattachées, {len(pending) - linked} non retrouvées."
            )
        )

    def _formation_for(self, experience):
        """The school's own catalogue first, the whole referential as a fallback."""
        if experience.school is not None:
            match = self._match(Formation.objects.taught_at(experience.school), experience.course)
            if match is not None:
                return match
        return self._match(Formation.objects.all(), experience.course)

    def _match(self, formations, course):
        """A same-name match, deterministic when the referential holds homonyms."""
        return formations.filter(name__iexact=course.strip()).order_by("onisep_id").first()
