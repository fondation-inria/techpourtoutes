from django.core.management.base import BaseCommand

from techpourtoutes.models import School
from techpourtoutes.services.school.flag_recommended_schools import FlagRecommendedSchools


class Command(BaseCommand):
    help = "Flag the schools matching one of the recommendation criteria"

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Ignorer quand des établissements sont déjà marqués.",
        )

    def handle(self, *args, **options):
        if options["if_empty"] and School.objects.filter(recommended=True).exists():
            self.stdout.write("  Établissements recommandés déjà marqués, mise à jour ignorée.")
            return

        FlagRecommendedSchools()
        self.stdout.write(self.style.SUCCESS("  Recommandation des établissements mise à jour."))
