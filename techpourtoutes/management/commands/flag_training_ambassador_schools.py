from django.core.management.base import BaseCommand

from techpourtoutes.models import School
from techpourtoutes.services.school.flag_training_ambassador_schools import (
    FlagTrainingAmbassadorSchools,
)


class Command(BaseCommand):
    help = "Flag the schools the ambassadrice funnel offers, from the curated Onisep id list"

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Ignorer quand des établissements sont déjà marqués.",
        )

    def handle(self, *args, **options):
        if options["if_empty"] and School.objects.training_ambassador().exists():
            self.stdout.write("  Établissements ambassadrice déjà marqués, mise à jour ignorée.")
            return

        FlagTrainingAmbassadorSchools()
        self.stdout.write(self.style.SUCCESS("  Éligibilité ambassadrice mise à jour."))
