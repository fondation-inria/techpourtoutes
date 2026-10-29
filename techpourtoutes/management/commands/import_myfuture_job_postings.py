import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import JobPosting
from techpourtoutes.services.job_posting.import_myfuture_job_postings import (
    ImportMyFutureJobPostings,
)
from techpourtoutes.tasks import import_myfuture_job_postings_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Mirror the MyFuture internships and job offers"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample",
            action="store_true",
            help="Make a single call to MyFuture: the first page of the offers.",
        )
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Skip the import if MyFuture offers are already in the database.",
        )
        parser.add_argument(
            # `async` is a Python keyword, so it cannot be the option's destination.
            "--async",
            dest="async_",
            action="store_true",
            help="Hand the import to the worker, which retries transient MyFuture failures.",
        )

    def handle(self, *args, **options):
        if options["async_"]:
            self._enqueue(options)
        else:
            self._import_now(options)

    def _enqueue(self, options):
        """Only the nightly cron runs it, and the cron runs on every app: production alone
        enables it."""
        if options["sample"] or options["if_empty"]:
            raise CommandError("  --sample et --if-empty ne s'appliquent qu'à l'import immédiat.")
        if not settings.SCHEDULED_IMPORTS_ENABLED:
            self.stdout.write("  Import planifié désactivé sur cette app.")
            return
        import_myfuture_job_postings_task.delay()
        self.stdout.write(self.style.SUCCESS("  Import enfilé sur le worker."))

    def _import_now(self, options):
        if options["if_empty"] and self._myfuture_postings().exists():
            self.stdout.write("  Des offres MyFuture sont déjà en base : import ignoré.")
            return

        result = ImportMyFutureJobPostings(sample=options["sample"])
        if result.failure:
            message = ", ".join(result.errors)
            logger.error("Import des offres MyFuture échoué : %s", message)
            raise CommandError(f"  {message}")
        count = self._myfuture_postings().count()
        self.stdout.write(self.style.SUCCESS(f"  {count} offres MyFuture en base."))

    @staticmethod
    def _myfuture_postings():
        return JobPosting.all_objects.filter(source=JobPosting.Source.MYFUTURE)
