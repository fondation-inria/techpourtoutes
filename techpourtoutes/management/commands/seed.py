from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import Pro


class Command(BaseCommand):
    help = "Seed the database with minimal dev data"

    def handle(self, *args, **options):
        if not settings.SEED_ENABLED:
            raise CommandError(
                "seed creates an account with a well-known-by-default password; it refuses "
                "to run unless SEED_ENABLED is set."
            )
        self._create_admin_pro()

    def _create_admin_pro(self):
        email = settings.SEED_ADMIN_EMAIL
        if Pro.objects.filter(email=email).exists():
            self.stdout.write(f"  Admin pro {email} already exists, skipping.")
            return
        pro = Pro(
            username=email,
            email=email,
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
        pro.set_password(settings.SEED_ADMIN_PASSWORD)
        pro.save(update_fields=["password"])
        self.stdout.write(
            self.style.SUCCESS(f"  Admin pro created: {email} / {settings.SEED_ADMIN_PASSWORD}")
        )
