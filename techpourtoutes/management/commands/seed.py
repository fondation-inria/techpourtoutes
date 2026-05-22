from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from techpourtoutes.models import Mentor

User = get_user_model()

ADMIN_EMAIL = "admin@techpourtoutes.io"
ADMIN_PASSWORD = "admin"

SAMPLE_MENTOR_EMAIL = "mentor@example.com"


class Command(BaseCommand):
    help = "Seed the database with minimal dev data"

    def handle(self, *args, **options):
        self._create_superuser()
        self._create_sample_mentor()

    def _create_superuser(self):
        if User.objects.filter(email=ADMIN_EMAIL).exists():
            self.stdout.write(f"  Superuser {ADMIN_EMAIL} already exists, skipping.")
            return
        User.objects.create_superuser(
            username=ADMIN_EMAIL, email=ADMIN_EMAIL, password=ADMIN_PASSWORD
        )
        self.stdout.write(
            self.style.SUCCESS(f"  Superuser created: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        )

    def _create_sample_mentor(self):
        if Mentor.objects.filter(email=SAMPLE_MENTOR_EMAIL).exists():
            self.stdout.write(f"  Sample mentor {SAMPLE_MENTOR_EMAIL} already exists, skipping.")
            return
        Mentor(
            username=SAMPLE_MENTOR_EMAIL,
            email=SAMPLE_MENTOR_EMAIL,
            first_name="Alice",
            last_name="Martin",
            civility=Mentor.Civility.MADAME,
            phone="+33612345678",
            postal_code="75001",
            professional_situation=Mentor.ProfessionalSituation.WORKING,
            structure_name="Acme Corp",
            job_title="CTO",
        ).save()
        self.stdout.write(self.style.SUCCESS(f"  Sample mentor created: {SAMPLE_MENTOR_EMAIL}"))
