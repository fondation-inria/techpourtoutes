import logging

from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.services.event.purge_orphan_event_images import PurgeOrphanEventImages

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Supprimer de l'object storage les visuels d'événements qu'aucun événement n'utilise : "
        "imports abandonnés, visuels remplacés, événements supprimés."
    )

    def handle(self, *args, **options):
        result = PurgeOrphanEventImages()
        if result.failure:
            message = ", ".join(result.errors)
            logger.error("Purge des visuels d'événements échouée : %s", message)
            raise CommandError(f"  {message}")
        self.stdout.write(
            self.style.SUCCESS(f"  {result.deleted} visuel(s) orphelin(s) supprimé(s).")
        )
