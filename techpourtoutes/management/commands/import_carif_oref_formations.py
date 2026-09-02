import logging

from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import Formation, FormationAction
from techpourtoutes.services.formation.import_carif_oref_formations import (
    ImportCarifOrefFormations,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import apprenticeship formations from the Carif-Oref catalogue"

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Ignorer l'import si le catalogue a déjà été importé.",
        )

    def handle(self, *args, **options):
        # A link without an Onisep identifier is one this import created: the Onisep steps run
        # before it and always fill Formation, so counting formations would never let it run.
        if options["if_empty"] and FormationAction.objects.filter(onisep_id__isnull=True).exists():
            self.stdout.write("  Catalogue Carif-Oref déjà importé, import ignoré.")
            return

        formations_before = Formation.objects.count()
        links_before = FormationAction.objects.count()
        result = ImportCarifOrefFormations()
        if result.failure:
            message = ", ".join(result.errors)
            logger.error("Import des formations Carif-Oref échoué : %s", message)
            raise CommandError(f"  {message}")
        self.stdout.write(
            self.style.SUCCESS(
                f"  {Formation.objects.count() - formations_before} formations créées, "
                f"{FormationAction.objects.count() - links_before} liens créés."
            )
        )
