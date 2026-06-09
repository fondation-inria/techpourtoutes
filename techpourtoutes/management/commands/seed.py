from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import Pro

ADMIN_EMAIL = "admin@techpourtoutes.io"
ADMIN_PASSWORD = "admin"


class Command(BaseCommand):
    help = "Seed the database with minimal dev data"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed creates an account with a well-known password and is for local "
                "development only; it refuses to run with DEBUG=False."
            )
        self._create_admin_pro()

    def _create_admin_pro(self):
        if Pro.objects.filter(email=ADMIN_EMAIL).exists():
            self.stdout.write(f"  Admin pro {ADMIN_EMAIL} already exists, skipping.")
            return
        pro = Pro(
            username=ADMIN_EMAIL,
            email=ADMIN_EMAIL,
            first_name="Admin",
            last_name="TechPourToutes",
            civility=Pro.Civility.MADAME,
            phone="+33600000000",
            postal_code="75001",
            professional_situation=Pro.ProfessionalSituation.WORKING,
            job_title="Admin",
            structure_name="Inria",
            is_superuser=True,
            is_staff=True,
        )
        pro.save()
        pro.set_password(ADMIN_PASSWORD)
        pro.save(update_fields=["password"])
        self.stdout.write(
            self.style.SUCCESS(f"  Admin pro created: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        )
