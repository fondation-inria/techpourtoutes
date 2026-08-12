import logging

from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import FormationAction
from techpourtoutes.services.formation_action.import_formation_actions import (
    ImportFormationActions,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import the links between formations and établissements from the Onisep open data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scope",
            default="all",
            choices=["all", *ImportFormationActions.SCOPES],
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
        if options["if_empty"] and FormationAction.objects.exists():
            self.stdout.write("  Actions de formation déjà importées, import ignoré.")
            return

        before = FormationAction.objects.count()
        result = ImportFormationActions(scope=options["scope"], sample=options["sample"])
        if result.failure:
            message = ", ".join(result.errors)
            logger.error("Import des actions de formation Onisep échoué : %s", message)
            raise CommandError(f"  {message}")
        self.stdout.write(
            self.style.SUCCESS(
                f"  {FormationAction.objects.count() - before} actions de formation créées."
            )
        )
