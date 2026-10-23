import logging

from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.services.storage.purge_orphan_images import PurgeOrphanImages

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Delete from the object storage the images no event nor makeuse project holds: "
        "abandoned uploads, replaced images, deleted records."
    )

    def handle(self, *args, **options):
        result = PurgeOrphanImages()
        if result.failure:
            message = ", ".join(result.errors)
            logger.error("Purge des visuels orphelins échouée : %s", message)
            raise CommandError(f"  {message}")
        self.stdout.write(
            self.style.SUCCESS(f"  {result.deleted} visuel(s) orphelin(s) supprimé(s).")
        )
