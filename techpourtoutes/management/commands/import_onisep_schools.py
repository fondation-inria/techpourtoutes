import logging

from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import School
from techpourtoutes.services.school.import_schools import ImportSchools

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import établissements from the Onisep open data into the School table"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scope",
            default="all",
            choices=["all", *ImportSchools.SCOPES],
            help="Sous-ensemble à importer.",
        )
        parser.add_argument(
            "--sample",
            action="store_true",
            help="Importer les échantillons commités au lieu d'interroger Onisep.",
        )
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Ignorer l'import si la table contient déjà des lignes.",
        )

    def handle(self, *args, **options):
        # The merge placeholders left by migration 0036 do not count as an import: skipping on
        # them would leave the very first import undone, with nothing for the remap to point at.
        if options["if_empty"] and School.objects.imported().exists():
            self.stdout.write("  Établissements déjà importés, import ignoré.")
            return

        before = School.objects.count()
        result = ImportSchools(scope=options["scope"], sample=options["sample"])
        if result.failure:
            message = ", ".join(result.errors)
            logger.error("Import des établissements Onisep échoué : %s", message)
            raise CommandError(f"  {message}")
        self.stdout.write(
            self.style.SUCCESS(f"  {School.objects.count() - before} établissements créés.")
        )
