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
        pro = Pro.objects.get(email=settings.SEED_ADMIN_EMAIL)
        today = timezone.localdate()
        for week, (lasts, fields) in enumerate(EVENT_SEEDS, start=1):
            start = today + timedelta(weeks=week)
            defaults = {
                "created_by": pro,
                "status": Event.Status.APPROVED,
                "access_type": Event.AccessType.OPEN,
                "start_date": start,
                "end_date": start + timedelta(days=lasts),
                "start_time": time(9, 0),
                "end_time": time(18, 0),
            }
            Event(**{**defaults, **fields}).save()
        self.stdout.write(self.style.SUCCESS(f"  {len(EVENT_SEEDS)} events created."))


# One per subcategory but `OTHER`, so the five card colours show up and the list spans more than
# one page: how many extra days it runs, then its fields.
EVENT_SEEDS = [
    (
        0,
        {
            "title": "Webinaire : les métiers de la cybersécurité à l'ère de l'IA",
            "organizer": "ANSSI",
            "subcategory": Event.Subcategory.WEBINAR,
            "location_type": Event.LocationType.ONLINE,
            "online_url": "https://example.org/webinaire-cyber",
            "access_type": Event.AccessType.REGISTRATION,
            "registration_url": "https://example.org/inscription-webinaire-cyber",
            "description": (
                "L'intelligence artificielle transforme les métiers de la cybersécurité, "
                "aussi bien du côté de la défense que de l'attaque.\n\n"
                "Au programme : un tour d'horizon des postes qui recrutent (analyste SOC, "
                "pentesteuse, réponse à incident) et les compétences à développer pour s'y "
                "préparer.\n\n"
                "Ce webinaire s'adresse à toute personne curieuse du sujet, aucun "
                "prérequis technique n'est nécessaire."
            ),
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
            "latitude": 48.8657,
            "longitude": 2.3752,
            "access_type": Event.AccessType.CANDIDACY,
            "registration_url": "https://example.org/candidature-job-dating",
            "description": (
                "Simplon organise une session de job dating dédiée aux développeuses web, "
                "en partenariat avec une dizaine d'entreprises partenaires.\n\n"
                "Chaque candidate rencontre plusieurs recruteuses lors d'entretiens courts "
                "de quinze minutes, sur des postes en CDI, alternance ou stage.\n\n"
                "La candidature se fait en amont : CV et courte présentation de ton "
                "parcours suffisent pour t'inscrire."
            ),
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
            "address": "Rue Gambetta",
            "postal_code": "94190",
            "city": "Villeneuve-Saint-Georges",
            "access_type": Event.AccessType.REGISTRATION,
            "registration_url": "https://example.org/inscription-forum-emploi",
            "latitude": 48.733123,
            "longitude": 2.458189,
            "description": (
                "France Travail organise un forum de l'emploi numérique réunissant des "
                "entreprises du territoire qui recrutent sur des métiers techniques.\n\n"
                "Développement, support informatique, gestion de projet : plus de trente "
                "postes seront à pourvoir en CDI, CDD et alternance.\n\n"
                "Pense à venir avec plusieurs exemplaires de ton CV, et à t'inscrire au "
                "préalable pour accéder aux entretiens flash."
            ),
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
            "latitude": 48.8927,
            "longitude": 2.3218,
            "access_type": Event.AccessType.REGISTRATION,
            "registration_url": "https://example.org/inscription-portes-ouvertes",
            "description": (
                "L'école 42 ouvre ses portes le temps d'une journée pour faire découvrir "
                "sa pédagogie par projets, sans professeurs ni cours magistraux.\n\n"
                "Au programme : visite des locaux, rencontre avec des étudiantes actuelles "
                "et présentation de la piscine, l'épreuve de sélection qui précède "
                "l'admission.\n\n"
                "Aucun diplôme n'est requis pour candidater : seule la motivation compte."
            ),
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
            "latitude": 44.8412,
            "longitude": -0.5701,
            "description": (
                "Duchess France t'invite à un afterwork convivial pour échanger avec "
                "d'autres femmes de la tech autour d'un verre.\n\n"
                "Pas de conférence ni de programme figé : l'objectif est simplement de se "
                "rencontrer, partager son parcours et élargir son réseau dans une ambiance "
                "détendue.\n\n"
                "Toutes les femmes travaillant ou souhaitant travailler dans la tech sont "
                "les bienvenues, quel que soit leur niveau d'expérience."
            ),
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
            "latitude": 45.7563,
            "longitude": 4.8547,
            "description": (
                "Latitudes organise un hackathon de 48 heures dédié aux projets tech à "
                "impact social et environnemental.\n\n"
                "En équipes pluridisciplinaires, les participantes développent un "
                "prototype répondant à une problématique posée par une association "
                "partenaire, avant de le présenter devant un jury.\n\n"
                "Débutantes ou confirmées, développeuses, designers ou chefs de projet : "
                "toutes les compétences sont utiles pour composer une équipe."
            ),
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
            "latitude": 48.8368,
            "longitude": 2.3868,
            "description": (
                "Femmes@Numérique propose une conférence sur les usages de "
                "l'intelligence artificielle au service de l'inclusion et de "
                "l'accessibilité.\n\n"
                "Trois intervenantes présenteront des projets concrets : outils "
                "d'accessibilité pour personnes en situation de handicap, détection des "
                "biais algorithmiques et IA au service de l'insertion professionnelle.\n\n"
                "Un temps d'échange avec le public clôturera la conférence."
            ),
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
            "description": (
                "Social Builder propose un atelier pratique pour retravailler son CV et "
                "son profil LinkedIn.\n\n"
                "Au programme : les codes attendus dans la tech, comment mettre en valeur "
                "un projet ou une reconversion, et les erreurs courantes à éviter.\n\n"
                "Viens avec ton CV actuel : l'atelier se termine par une session de "
                "retours personnalisés en petits groupes."
            ),
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
            "description": (
                "Le Wagon réunit trois femmes reconverties dans la data pour une table "
                "ronde sur leur parcours.\n\n"
                "Ancienne comptable, ex-professeure et ex-commerciale : elles reviennent "
                "sur les raisons de leur reconversion, la formation choisie et les "
                "premiers mois dans leur nouveau métier de data analyst ou data "
                "scientist.\n\n"
                "Un temps de questions-réponses permettra d'échanger directement avec "
                "elles sur les financements et les débouchés."
            ),
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
            "latitude": 43.6112,
            "longitude": 1.4351,
            "description": (
                "Numeum organise une session de speed dating entre recruteuses et "
                "développeuses, sur le principe d'entretiens courts et enchaînés.\n\n"
                "Chaque candidate rencontre entre huit et dix entreprises du numérique "
                "toulousain en une seule soirée, sur des postes en CDI ou alternance.\n\n"
                "L'événement est ouvert à tous les niveaux d'expérience, de la junior à la "
                "développeuse confirmée en recherche de nouveaux défis."
            ),
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
            "latitude": 43.2762,
            "longitude": 5.3838,
            "description": (
                "L'Onisep organise le salon de l'orientation post-bac au Parc Chanot, "
                "réunissant lycées, écoles et universités de la région.\n\n"
                "Lycéennes et étudiantes pourront y rencontrer des établissements de "
                "formation, assister à des conférences métiers et échanger avec des "
                "étudiantes déjà engagées dans le supérieur.\n\n"
                "Un espace est spécifiquement dédié aux filières numériques et "
                "scientifiques, encore trop peu choisies par les filles."
            ),
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
            "latitude": 50.6912,
            "longitude": 3.1706,
            "description": (
                "OVHcloud ouvre son campus de Roubaix pour une learning expédition d'une "
                "journée à la découverte de ses métiers du cloud.\n\n"
                "Au programme : visite du datacenter, rencontres avec des équipes "
                "infrastructure, sécurité et développement, et ateliers pratiques sur les "
                "enjeux de la souveraineté numérique.\n\n"
                "Cette immersion s'adresse aux étudiantes et jeunes diplômées "
                "curieuses des métiers techniques du cloud."
            ),
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
            "latitude": 48.5876,
            "longitude": 7.7392,
            "description": (
                "Epitech ouvre les portes de son campus strasbourgeois pour une visite "
                "guidée par des étudiantes actuelles.\n\n"
                "Au programme : découverte des locaux et des projets pédagogiques en "
                "cours, présentation du cursus et de ses spécialisations, puis un temps "
                "d'échange libre pour poser toutes vos questions.\n\n"
                "La visite convient aussi bien aux lycéennes en pleine réflexion "
                "d'orientation qu'aux personnes en reconversion."
            ),
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
            "latitude": 48.1088,
            "longitude": -1.7192,
            "description": (
                "Thales propose une immersion d'une demi-journée aux côtés d'une "
                "ingénieure systèmes embarqués sur son site rennais.\n\n"
                "Tu suivras son quotidien sur des projets de défense et de sécurité, de la "
                "conception logicielle aux tests d'intégration sur du matériel réel.\n\n"
                "Cette immersion s'adresse aux étudiantes en école d'ingénieures ou en "
                "cursus informatique souhaitant découvrir ce métier de l'intérieur."
            ),
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
            "latitude": 43.6177,
            "longitude": 3.8703,
            "description": (
                "Class'Code organise la cérémonie annuelle de remise des prix Codeuses, "
                "qui récompense des projets tech portés par des femmes.\n\n"
                "Cinq lauréates seront distinguées dans des catégories allant du projet "
                "étudiant à l'initiative associative, en présence de marraines issues de "
                "l'écosystème tech local.\n\n"
                "La soirée se poursuit par un cocktail networking ouvert à toutes les "
                "personnes présentes."
            ),
            "price": Decimal("18.90"),
        },
    ),
    (
        4,
        {
            "title": "Vis-ma-vie d'ingénieure IA",
            "organizer": "Thales",
            "subcategory": Event.Subcategory.JOB_SHADOWING,
            "location_type": Event.LocationType.PHYSICAL,
            "address": "4 avenue des Louvresses",
            "postal_code": "35000",
            "city": "Rennes",
            "latitude": 48.1088,
            "longitude": -1.7192,
            "description": (
                "Thales propose une nouvelle session vis-ma-vie, cette fois aux côtés "
                "d'une ingénieure en intelligence artificielle.\n\n"
                "Au programme : conception de modèles de détection pour des applications "
                "de défense, entraînement et évaluation des algorithmes, et échanges avec "
                "l'équipe recherche sur les enjeux éthiques de l'IA.\n\n"
                "Une journée idéale pour découvrir un métier d'avenir, sans prérequis "
                "en machine learning."
            ),
            "price": Decimal("0"),
        },
    ),
]
