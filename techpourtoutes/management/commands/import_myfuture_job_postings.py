import logging

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
            # `async` is a Python keyword, so it cannot be the option's destination.
            "--async",
            dest="async_",
            action="store_true",
            help="Déléguer l'import au worker, qui rejouera les pannes passagères de MyFuture.",
        )

    def handle(self, *args, **options):
        if options["async_"]:
            import_myfuture_job_postings_task.delay()
            self.stdout.write(self.style.SUCCESS("  Import enfilé sur le worker."))
            return

        result = ImportMyFutureJobPostings()
        if result.failure:
            message = ", ".join(result.errors)
            logger.error("Import des offres MyFuture échoué : %s", message)
            raise CommandError(f"  {message}")
        count = JobPosting.objects.filter(source=JobPosting.Source.MYFUTURE).count()
        self.stdout.write(self.style.SUCCESS(f"  {count} offres MyFuture en base."))
