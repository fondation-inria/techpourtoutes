from datetime import date, time, timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from techpourtoutes.models import (
    Event,
    Formation,
    Level,
    MakeuseProject,
    Pro,
    TrainingExperience,
)
from techpourtoutes.models.beneficiary import Beneficiary
from techpourtoutes.models.makeuse_project import IMAGE_PREFIX
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
        if settings.SEED_TEAM_EMAILS:
            self._create_team_accounts()
        else:
            self._create_default_accounts()
        self._create_events()
        self._create_makeuse_projects()

    def _import_onisep_samples(self):
        call_command("import_schools_and_formations", sample=True, if_empty=True)

    def _create_default_accounts(self):
        self._create_admin_pro(settings.SEED_ADMIN_EMAIL, first_name="Admin")
        self._create_beneficiary(
            settings.SEED_BENEFICIARY_EMAIL,
            first_name="Beneficiary",
            birth_date=None,
            level=Level.TERMINALE,
            formations=Formation.objects.secondary(),
        )

    def _create_team_accounts(self):
        today = timezone.localdate()
        for email in settings.SEED_TEAM_EMAILS:
            self._create_beneficiary(
                _alias(email, "etudiante"),
                first_name="Étudiante",
                birth_date=date(today.year - 20, 1, 1),
                level=Level.BAC_2,
                formations=Formation.objects.higher_ed(),
            )
            self._create_beneficiary(
                _alias(email, "lyceenne"),
                first_name="Lycéenne",
                birth_date=date(today.year - 16, 1, 1),
                level=Level.PREMIERE,
                formations=Formation.objects.secondary(),
            )
            self._create_admin_pro(_alias(email, "pro"), first_name="Pro")

    def _create_admin_pro(self, email, *, first_name):
        if Pro.objects.filter(email=email).exists():
            self.stdout.write(f"  Admin pro {email} already exists, skipping.")
            return
        pro = Pro(
            username=email,
            email=email,
            first_name=first_name,
            last_name="TechPourToutes",
            civility=Pro.Civility.MADAME,
            phone="+33600000000",
            postal_code="75001",
            structure_type=Pro.StructureType.PUBLIC_INSTITUTION,
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

    def _create_beneficiary(self, email, *, first_name, birth_date, level, formations):
        if Beneficiary.objects.filter(email=email).exists():
            self.stdout.write(f"  Beneficiary {email} already exists, skipping.")
            return
        beneficiary = Beneficiary(
            username=email,
            email=email,
            first_name=first_name,
            last_name="TechPourToutes",
            civility=Beneficiary.Civility.MADAME,
            birth_date=birth_date,
            phone="+33600000000",
            postal_code="75001",
        )
        beneficiary.save()
        beneficiary.save(update_fields=["password"])

        formation = formations.order_by("name").first()
        TrainingExperience.objects.create(
            user=beneficiary,
            school=formation.schools.order_by("name").first(),
            formation=formation,
            level=level,
            start_date=current_school_year_start_date(),
            end_date=current_school_year_end_date(),
        )
        self.stdout.write(self.style.SUCCESS(f"  Beneficiary created: {email}"))

    def _create_events(self):
        """Approved and upcoming, one a week: enough of them to scroll past the first page."""
        pro = Pro.objects.filter(is_superuser=True).earliest("created_at")
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

    def _create_makeuse_projects(self):
        for fields in MAKEUSE_PROJECT_SEEDS:
            title = fields["title"]
            if MakeuseProject.objects.filter(title=title).exists():
                self.stdout.write(f"  Makeuse project {title} already exists, skipping.")
                continue
            fields = dict(fields)
            image_path = settings.BASE_DIR / fields.pop(
                "image", "ui/static/images/events/social/afterwork.webp"
            )
            project = MakeuseProject(**fields)
            with open(image_path, "rb") as image:
                project.image.save(f"{IMAGE_PREFIX}/{uuid4().hex}{image_path.suffix}", File(image))
            self.stdout.write(self.style.SUCCESS(f"  Makeuse project created: {title}"))


MAKEUSE_PROJECT_SEEDS = [
    {
        "title": "Stage Finder",
        "category": MakeuseProject.Category.APPS_AND_WEB,
        "project_type": "Application mobile",
        "creator_name": "Inès Benali",
        "contact_email": "ines.benali@example.org",
        "demo_url": "https://example.org/stage-finder",
        "idea": (
            "Une appli qui rapproche les lycéennes des entreprises de leur quartier pour "
            "trouver un stage de seconde.\n\n"
            "On filtre par métier, par distance et par durée, et on contacte l'entreprise "
            "directement depuis l'appli."
        ),
        "background": (
            "Terminale STI2D à Amiens. J'ai galéré à trouver mon propre stage, c'est ce qui "
            "m'a donné l'idée."
        ),
        "methodology": (
            "Des entretiens avec une dizaine de lycéennes, une maquette sur Figma, puis "
            "l'application développée avec Flutter."
        ),
        "hobbies": "Le volley, le dessin et les escape games.",
    },
    {
        "title": "Cyber Quiz",
        "category": MakeuseProject.Category.APPS_AND_WEB,
        "project_type": "Site web",
        "creator_name": "Léa Martin",
        "contact_email": "lea.martin@example.org",
        "demo_url": "https://example.org/cyber-quiz",
        "idea": (
            "Un quiz pour apprendre les bons réflexes de cybersécurité en dix minutes : mots de "
            "passe, hameçonnage, réseaux publics.\n\n"
            "Chaque réponse est suivie d'une courte explication pour retenir l'essentiel."
        ),
        "background": "BUT informatique à Lannion, option cybersécurité.",
        "methodology": (
            "Développé avec Django et HTMX, puis testé auprès de ma famille et de mes amies, "
            "qui n'y connaissaient rien."
        ),
        "hobbies": "Les CTF, la randonnée et les romans policiers.",
    },
    {
        "title": "Mentora",
        "category": MakeuseProject.Category.APPS_AND_WEB,
        "project_type": "Plateforme",
        "creator_name": "Aminata Diallo",
        "contact_email": "aminata.diallo@example.org",
        "demo_url": "https://example.org/mentora",
        "idea": (
            "Une plateforme pour trouver une mentore dans la tech quand on ne connaît "
            "personne dans le milieu.\n\n"
            "On décrit son projet en quelques lignes, et la plateforme propose trois mentores "
            "dont le parcours y ressemble."
        ),
        "background": (
            "BTS SIO à Lyon. Pendant mes deux années, j'ai vu beaucoup de camarades abandonner "
            "faute de savoir vers qui se tourner."
        ),
        "methodology": (
            "Au départ un simple tableur partagé, puis un site statique, et enfin une vraie "
            "application avec des comptes. Les retours des premières utilisatrices ont changé "
            "presque toutes mes idées de départ."
        ),
        "hobbies": "La danse, la photo argentique et les podcasts sur l'histoire des sciences.",
    },
    {
        "title": "Data Vélo",
        "category": MakeuseProject.Category.DATA_AND_AI,
        "project_type": "Data visualisation",
        "creator_name": "Chloé Nguyen",
        "contact_email": "chloe.nguyen@example.org",
        "demo_url": "https://example.org/data-velo",
        "idea": (
            "Visualiser les trajets en vélo partagé de ma ville pour repérer où il manque des "
            "stations."
        ),
        "background": "Reconversion après huit ans comme comptable, formation data analyst.",
        "methodology": "L'open data de la métropole, Python, pandas et une carte Leaflet.",
        "hobbies": "Le vélo, évidemment, et la pâtisserie.",
    },
    {
        "title": "Robot trieur",
        "category": MakeuseProject.Category.OBJECTS_AND_ROBOTICS,
        "project_type": "Objet connecté",
        "creator_name": "Sarah Cohen",
        "contact_email": "sarah.cohen@example.org",
        "demo_url": "https://example.org/robot-trieur",
        "idea": "Un petit robot qui trie les déchets de la cantine grâce à une caméra.",
        "background": "Première générale, spécialités NSI et physique-chimie.",
        "methodology": (
            "Une carte Arduino, un modèle de reconnaissance d'images entraîné sur nos propres "
            "photos, et beaucoup de carton."
        ),
        "hobbies": "La robotique et le théâtre.",
    },
    {
        "title": "Chatbot orientation",
        "category": MakeuseProject.Category.DATA_AND_AI,
        "project_type": "Intelligence artificielle",
        "creator_name": "Emma Petit",
        "contact_email": "emma.petit@example.org",
        "demo_url": "https://example.org/chatbot-orientation",
        "idea": (
            "Un chatbot qui répond aux questions des lycéennes sur les formations du "
            "numérique, à partir des fiches de l'Onisep."
        ),
        "background": "Licence de mathématiques à Grenoble, puis master en science des données.",
        "methodology": (
            "Une base de fiches formations, un moteur de recherche sémantique et une interface "
            "web toute simple."
        ),
        "hobbies": "L'escalade et les échecs.",
    },
    {
        "title": "Pixel Garden",
        "category": MakeuseProject.Category.GAMES,
        "project_type": "Jeu vidéo",
        "creator_name": "Manon Lefèvre",
        "contact_email": "manon.lefevre@example.org",
        "demo_url": "https://example.org/pixel-garden",
        "idea": (
            "Un jeu de jardinage en pixel art pour apprendre les bases de la programmation : "
            "on arrose et on plante en écrivant de petites instructions."
        ),
        "background": "Bac pro, puis BTS en alternance dans une PME de développement web.",
        "methodology": "Godot, des sprites dessinés à la main et des tests en classe de collège.",
        "hobbies": "Le jardinage, pour de vrai, et les jeux indépendants.",
    },
    {
        "title": "L'aventure Tech",
        "category": MakeuseProject.Category.GAMES,
        "project_type": "Jeu vidéo",
        "creator_name": "Océane Deneuville",
        "contact_email": "o.deneuville@myskolae.fr",
        "demo_url": "https://ocednv.itch.io/tpt",
        "image": "data/seed/laventure_tech.webp",
        "idea": (
            "L'idée est simple : un jeu pédagogique pour montrer aux filles que se lancer dans la "
            "tech c'est possible. Concrètement, il y a 3 parcours différents selon le profil : "
            "les lycéennes, les étudiantes, et les filles en reconversion.\n\n"
            "Le principe : à chaque étape, une situation est donnée et tu dois choisir entre 2 "
            "choix. Il n'y a pas de bonne ou de mauvaise réponse. Le vrai objectif c'est de "
            "garder tes 4 jauges au-dessus de zéro. Un peu comme dans la vraie vie, chaque "
            "décision a un impact, et il faut réussir à trouver l'équilibre."
        ),
        "background": (
            "Mon parcours a été loin d'être linéaire : bac général avec des spécialités un peu "
            "aléatoires pour finir en Game Design : LLCE anglais, SES et HGGSP. Après le bac "
            "j'étais complètement perdue, donc j'ai fait ce qu'on fait tous : j'ai pris la "
            "matière où j'avais les meilleures notes. Direction LEA anglais-espagnol à Nanterre. "
            "Sauf qu'en espagnol, je ne suis pas très forte donc j'ai arrêté au bout d'un an.\n\n"
            "Ensuite j'ai retenté avec ma deuxième matière préférée au lycée : la philo, à la "
            "Sorbonne Panthéon. Alors ouais, ça fait son petit effet quand tu le dis en soirée, "
            "mais je me voyais clairement pas faire ça toute ma vie. Nouvel arrêt au bout d'un "
            "an.\n\n"
            "Et là, dernière tentative, dernière chance : je me tourne vers une école de jeux "
            "vidéo. Direction l'ICAN, où je vais bientôt attaquer ma dernière année de Bachelor. "
            "Et franchement c'est vraiment bien parce que c'est hyper pluridisciplinaire : du "
            "code, du game design, de l'UX, de la 3D, de l'histoire de l'art... il y a un peu de "
            "tout.\n\n"
            "À travers mon parcours, j'espère montrer que même quand le chemin n'est pas tout "
            "droit, on peut finir par trouver sa place."
        ),
        "methodology": (
            "Ce jeu a été réalisé dans le cadre de mon stage chez TechPourToutes. Je l'ai "
            "développé sur Unity, un moteur de jeu, en y consacrant une journée par semaine "
            "pendant environ deux mois.\n\n"
            "J'ai commencé par une phase de recherche, principalement autour des jauges : il "
            "fallait choisir celles qui représentaient le mieux les enjeux d'un parcours dans la "
            "tech, et réfléchir à la manière dont elles pouvaient évoluer selon les choix de la "
            "joueuse. J'ai ensuite étudié plusieurs jeux de référence pour m'inspirer de leurs "
            "mécaniques et de leur narration. Une fois ces bases posées, j'ai écrit le scénario, "
            "puis je suis rapidement passée à un prototype jouable, que j'ai amélioré et peaufiné "
            "tout au long du projet, jusqu'à la version finale.\n\n"
            "En parallèle, j'ai rencontré des professionnels du jeu vidéo pour avoir leur regard "
            "sur mon travail. Comme il s'agit d'un jeu pédagogique, je voulais m'assurer que le "
            "contenu était juste et pertinent, tout en trouvant le bon équilibre : transmettre "
            "des messages sans trop en dire, pour que le jeu reste avant tout une expérience à "
            "vivre et non une leçon."
        ),
        "hobbies": (
            "Côté loisirs j'aime beaucoup les jeux vidéo (sans surprise vu mes études), et j'aime "
            "bien faire du basket. Sinon je suis plutôt sociable donc j'adore sortir boire des "
            "verres avec mes amis, et niveau musique j'adore jouer de la guitare, j'ai même un "
            "tatouage de la guitare de Jimmy Hendrix."
        ),
    },
]


def _alias(email, tag):
    """`test@example.com` tagged `pro` is `test+pro@example.com`, delivered to the same inbox."""
    local, domain = email.split("@")
    return f"{local}+{tag}@{domain}"


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
]
