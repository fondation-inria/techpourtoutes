from datetime import time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from techpourtoutes.models import Event, Formation, Level, Pro, TrainingExperience
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
        self._create_events()

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

        formation = Formation.objects.secondary().order_by("name").first()
        TrainingExperience.objects.create(
            user=beneficiary,
            school=formation.schools.order_by("name").first(),
            formation=formation,
            level=Level.TERMINALE,
            start_date=current_school_year_start_date(),
            end_date=current_school_year_end_date(),
        )
        self.stdout.write(self.style.SUCCESS(f"  Beneficiary created: {email}"))

    def _create_events(self):
        """Approved and upcoming, one a week: enough of them to scroll past the first page."""
        if Event.objects.exists():
            self.stdout.write("  Events already exist, skipping.")
            return
        pro = Pro.objects.get(email=settings.SEED_ADMIN_EMAIL)
        today = timezone.localdate()
        for week, (lasts, fields) in enumerate(EVENT_SEEDS, start=1):
            start = today + timedelta(weeks=week)
            Event(
                created_by=pro,
                status=Event.Status.APPROVED,
                access_type=Event.AccessType.OPEN,
                start_date=start,
                end_date=start + timedelta(days=lasts),
                start_time=time(9, 0),
                end_time=time(18, 0),
                **fields,
            ).save()
        self.stdout.write(self.style.SUCCESS(f"  {len(EVENT_SEEDS)} events created."))


# One per subcategory but `OTHER`, so the five card colours show up and the list spans more than
# one page: how many extra days it runs, then its fields.
EVENT_SEEDS = [
    (
        0,
        {
            "title": "Webinaire : les métiers de la cybersécurité",
            "organizer": "ANSSI",
            "subcategory": Event.Subcategory.WEBINAR,
            "location_type": Event.LocationType.ONLINE,
            "online_url": "https://example.org/webinaire-cyber",
            "price": Decimal("0"),
        },
    ),
    (
        0,
        {
            "title": "Job dating développeuses web",
            "organizer": "Simplon",
            "subcategory": Event.Subcategory.JOB_DATING,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "12 rue de la Fontaine au Roi",
            "postal_code": "75011",
            "city": "Paris",
            "price": Decimal("0"),
        },
    ),
    (
        2,
        {
            "title": "Portes ouvertes de l'école 42",
            "organizer": "École 42",
            "subcategory": Event.Subcategory.OPEN_HOUSE,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "96 boulevard Bessières",
            "postal_code": "75017",
            "city": "Paris",
            "price": Decimal("0"),
        },
    ),
    (
        0,
        {
            "title": "Afterwork des femmes de la tech",
            "organizer": "Duchess France",
            "subcategory": Event.Subcategory.AFTERWORK,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "5 place de la Bourse",
            "postal_code": "33000",
            "city": "Bordeaux",
            "price": Decimal("12.50"),
        },
    ),
    (
        1,
        {
            "title": "Hackathon Tech For Good",
            "organizer": "Latitudes",
            "subcategory": Event.Subcategory.HACKATHON,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "27 rue du Chemin Vert",
            "postal_code": "69003",
            "city": "Lyon",
            "price": Decimal("0"),
        },
    ),
    (
        0,
        {
            "title": "Conférence : l'IA au service de l'inclusion",
            "organizer": "Femmes@Numérique",
            "subcategory": Event.Subcategory.CONFERENCE,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "2 rue Simone Iff",
            "postal_code": "75012",
            "city": "Paris",
            "price": Decimal("0"),
        },
    ),
    (
        0,
        {
            "title": "Atelier CV et profil LinkedIn",
            "organizer": "Social Builder",
            "subcategory": Event.Subcategory.WORKSHOP,
            "location_type": Event.LocationType.ONLINE,
            "online_url": "https://example.org/atelier-cv",
            "price": Decimal("0"),
        },
    ),
    (
        0,
        {
            "title": "Table ronde : réussir sa reconversion vers la data",
            "organizer": "Le Wagon",
            "subcategory": Event.Subcategory.ROUND_TABLE,
            "location_type": Event.LocationType.ONLINE,
            "online_url": "https://example.org/table-ronde-data",
            "price": Decimal("0"),
        },
    ),
    (
        1,
        {
            "title": "Forum de l'emploi numérique",
            "organizer": "France Travail",
            "subcategory": Event.Subcategory.JOB_FAIR,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "1 place François Mitterrand",
            "postal_code": "59000",
            "city": "Lille",
            "price": Decimal("0"),
        },
    ),
    (
        0,
        {
            "title": "Speed dating recruteurs et développeuses",
            "organizer": "Numeum",
            "subcategory": Event.Subcategory.SPEED_DATING,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "6 allée Jean-Baptiste Doumeng",
            "postal_code": "31000",
            "city": "Toulouse",
            "price": Decimal("0"),
        },
    ),
    (
        2,
        {
            "title": "Salon de l'orientation post-bac",
            "organizer": "Onisep",
            "subcategory": Event.Subcategory.SALON,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "Parc Chanot, rond-point du Prado",
            "postal_code": "13008",
            "city": "Marseille",
            "price": Decimal("5"),
        },
    ),
    (
        0,
        {
            "title": "Learning expédition chez OVHcloud",
            "organizer": "OVHcloud",
            "subcategory": Event.Subcategory.LEARNING_EXPEDITION,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "2 rue Kellermann",
            "postal_code": "59100",
            "city": "Roubaix",
            "price": Decimal("0"),
        },
    ),
    (
        0,
        {
            "title": "Visite du campus Epitech",
            "organizer": "Epitech",
            "subcategory": Event.Subcategory.VISIT,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "4 rue de Dettwiller",
            "postal_code": "67000",
            "city": "Strasbourg",
            "price": Decimal("0"),
        },
    ),
    (
        4,
        {
            "title": "Vis-ma-vie d'ingénieure systèmes embarqués",
            "organizer": "Thales",
            "subcategory": Event.Subcategory.JOB_SHADOWING,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "4 avenue des Louvresses",
            "postal_code": "35000",
            "city": "Rennes",
            "price": Decimal("0"),
        },
    ),
    (
        0,
        {
            "title": "Cérémonie de remise des prix Codeuses",
            "organizer": "Class'Code",
            "subcategory": Event.Subcategory.CEREMONY,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "163 rue Auguste Broussonnet",
            "postal_code": "34000",
            "city": "Montpellier",
            "price": Decimal("18.90"),
        },
    ),
]
