from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from techpourtoutes.models import Formation, Level, Pro, School, TrainingExperience
from techpourtoutes.models.beneficiary import Beneficiary
from techpourtoutes.utils.school_year import (
    current_school_year_end_date,
    current_school_year_start_date,
)


class Command(BaseCommand):
    help = "Seed the database with minimal dev data"

    def handle(self, *args, **options):
        if not settings.SEED_ENABLED:
            raise CommandError(
                "seed creates an account with a well-known-by-default password; it refuses "
                "to run unless SEED_ENABLED is set."
            )
        self._import_onisep_samples()
        self._create_admin_pro()
        self._create_beneficiary()

    def _import_onisep_samples(self):
        call_command("import_schools_and_formations", sample=True, if_empty=True)

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

    def _create_beneficiary(self):
        email = settings.SEED_BENEFICIARY_EMAIL
        if Beneficiary.objects.filter(email=email).exists():
            self.stdout.write(f"  Beneficiary {email} already exists, skipping.")
            return
        beneficiary = Beneficiary(
            username=email,
            email=email,
            first_name="Beneficiary",
            last_name="TechPourToutes",
            civility=Beneficiary.Civility.MADAME,
            phone="+33600000000",
            postal_code="75001",
        )
        beneficiary.save()
        beneficiary.save(update_fields=["password"])

        school = School.objects.secondary().order_by("name").first()
        TrainingExperience.objects.create(
            user=beneficiary,
            school=school,
            formation=Formation.objects.taught_at(school).order_by("name").first(),
            level=Level.TERMINALE,
            start_date=current_school_year_start_date(),
            end_date=current_school_year_end_date(),
        )
        self.stdout.write(self.style.SUCCESS(f"  Beneficiary created: {email}"))
