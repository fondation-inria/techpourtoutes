import logging

from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import Formation
from techpourtoutes.services.formation.import_formations import ImportFormations

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import formations from the Onisep open data into the Formation table"

    def add_arguments(self, parser):
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
        if options["if_empty"] and Formation.objects.exists():
            self.stdout.write("  Formations déjà importées, import ignoré.")
            return

        before = Formation.objects.count()
        result = ImportFormations(sample=options["sample"])
        if result.failure:
            message = ", ".join(result.errors)
            logger.error("Import des formations Onisep échoué : %s", message)
            raise CommandError(f"  {message}")
        self.stdout.write(
            self.style.SUCCESS(f"  {Formation.objects.count() - before} formations créées.")
        )
