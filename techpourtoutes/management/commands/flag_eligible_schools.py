from django.core.management.base import BaseCommand

from techpourtoutes.models import School
from techpourtoutes.services.school.flag_eligible_schools import FlagEligibleSchools


class Command(BaseCommand):
    help = "Flag the schools matching one of the eligibility criteria"

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Ignorer quand des établissements sont déjà marqués.",
        )

    def handle(self, *args, **options):
        if options["if_empty"] and School.objects.filter(eligible=True).exists():
            self.stdout.write("  Établissements éligibles déjà marqués, mise à jour ignorée.")
            return

        FlagEligibleSchools()
        self.stdout.write(self.style.SUCCESS("  Éligibilité des établissements mise à jour."))
