# TechPourToutes

Plateforme web Django pour la communauté TechPourToutes.

## Stack technique

- **Python 3.14** / **Django 6**
- **uv** pour la gestion des dépendances
- **PostgreSQL**
- **Ruff** pour le linting et le formatage
- **Tailwind CSS** + **DaisyUI** (via django-tailwind-cli)
- **django-cotton** pour les composants UI
- **django-otp** pour la double authentification (2FA) de l'admin
- **django-axes** pour le verrouillage du login admin après échecs répétés

## Structure du projet

```
conf/               # Configuration Django (settings, urls, wsgi/asgi)
techpourtoutes/     # Application principale
  models/
  views/
  services/
  templates/
  tests/
  forms.py
ui/                 # Design system
  static/css/       # Source CSS Tailwind
  svg_source/       # Icônes SVG sources (buildées dans un sprite dans le dossier static)
  templates/cotton/ # Composants django-cotton
```

## Installation

### Prérequis

- Python 3.14
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- PostgreSQL

```bash
# cloner le projet
gh repo clone fondation-inria/techpourtoutes

cd techpourtoutes

# setup complet (DB, .env, migrations, hooks pre-commit, seed)
make install
```

`make install` est idempotent : relancé sur un projet déjà installé, il ignore ce qui existe déjà et le signale en console.

> Le `DATABASE_URL` dans `.env` est configuré automatiquement avec votre nom d'utilisateur système (`whoami`). Si votre utilisateur PostgreSQL local est différent, ajustez-le manuellement dans `.env`.

Pour une installation manuelle step by step, `make install` lance les commandes suivantes :

```bash
# installer les dépendances
uv sync --group dev

# créer la db postgresql
createdb techpourtoutes

# configurer les variables d'environnement dans le .env
cp .env.example .env

# ! renseigner l'url de db locale dans le .env avant de continuer (changer l'username suffit normalement)
uv run python manage.py migrate
uv run python manage.py createsuperuser

# installer les hooks pre-commit
uv run pre-commit install

# seed la db
uv run python manage.py seed
```

## Lancer le projet en développement

Il faut deux processus : le serveur Django et le watcher Tailwind. Les deux peuvent tourner ensemble avec la commande

```bash
make run # lance uv run python manage.py tailwind runserver
```

Le premier lancement installera Tailwind CSS CLI si nécessaire.
L'application est disponible sur [http://localhost:8000](http://localhost:8000).

## Commandes utiles

Un `Makefile` expose des raccourcis pour les commandes courantes :

```bash
make install      # setup complet (première installation)
make sync         # installer/mettre à jour les dépendances et lancer les migrations
make run          # lancer le serveur de dev avec le watcher Tailwind
make test         # lancer les tests
make lint         # linter avec ruff
make format       # formater avec ruff
make pre-commit   # lancer les hooks pre-commits manuellement (lint + format)
make icons        # rebuilder le sprite SVG
make seed         # peupler la DB avec des données minimales de dev
```

## Tester les emails en local

En développement (`DEBUG=True` et `USE_BREVO=False`), Django envoie les emails via SMTP sur `localhost:1025`. [Mailpit](https://mailpit.axllent.org/) intercepte ces emails et les affiche dans une interface web.

> La connexion des users passe par un lien magique envoyé par email — Mailpit est donc **nécessaire** pour s'authentifier en local.

```bash
# Installer Mailpit
brew install mailpit
# to run automatically in the background
brew services start mailpit
# or to run it manually
mailpit
```

L'interface est disponible sur [http://localhost:8025](http://localhost:8025). Tous les emails envoyés par l'application y apparaissent.

> En production, les emails sont envoyés via [Brevo](https://www.brevo.com/) (Anymail). La variable `BREVO_API_KEY` doit être renseignée dans le `.env` et `USE_BREVO` doit être défini à True.

## Rate limiting (anti-abus)

L'endpoint POST `login_request` est throttlés **en production** (désactivé en local, `DEBUG=True`) **par email** pour éviter le spam (défaut `5 tentatives/300 secondes`). Au-delà de la limite : réponse `HTTP 429`.

Les compteurs vivent dans le cache Redis : **en production**, définir `CACHE_URL` vers une URL Redis, si possible dans une base logique différente de celle utilisée par Celery si les deux utilisent le même Redis

## Admin

Par défaut, l'interface d'administration Django est servie sur `/admin/`. En production, l'url est déterminée par la variable d'environnement `ADMIN_URL` (ex. `ADMIN_URL=mon-chemin-prive`).

### Double authentification (2FA)

En production, l'accès à l'admin exige un second facteur TOTP en plus du mot de passe, via [django-otp](https://github.com/django-otp/django-otp). En local, la 2FA est désactivée : le formulaire de connexion standard suffit. Pour enregistrer un appareil :

```bash
uv run python manage.py add_totp_device <email>
```

La commande crée un appareil TOTP confirmé et affiche la clé secrète à saisir manuellement dans l'application d'authentification.

### Verrouillage après échecs répétés

En production, [django-axes](https://github.com/jazzband/django-axes) verrouille le login admin après plusieurs échecs de mot de passe (anti-brute-force). Le verrouillage est scopé au couple (identifiant, IP) — personne ne peut donc bloquer un admin de façon globale — et expire automatiquement après `AXES_COOLOFF_TIME` (1 h). Désactivé en local (`DEBUG`).

Variables : `AXES_FAILURE_LIMIT` (défaut 5), `AXES_ENABLED` (défaut : activé hors `DEBUG`). Pour lever un verrou manuellement : `uv run python manage.py axes_reset`.

## Icônes SVG

Les icônes sont regroupées dans un sprite SVG généré automatiquement.

**Ajouter une icône :**

1. Déposer le fichier `.svg` dans `ui/svg_source/` — le nom du fichier devient l'identifiant de l'icône (ex. `mon-icone.svg`).
2. Rebuilder le sprite :

```bash
make icons
```

Le sprite est écrit dans `ui/static/svg/sprite.svg`.

**Utiliser une icône dans un template :**

```html
<c-components.icon name="mon-icone" class="size-6" />
```

Le composant cotton `ui/templates/cotton/icon.html` génère un `<svg><use>` qui pointe vers le sprite.

## Synchronisation des contacts Brevo

À la création/mise à jour/suppression d'un `Pro`, un signal déclenche une tâche Celery qui synchronise le contact dans Brevo (liste configurée via `BREVO_PRO_LIST_ID`).

La synchro est désactivée par défaut en local (`BREVO_SYNC_ENABLED=False`). Pour l'activer (en prod ou pour tester en local), passer `BREVO_SYNC_ENABLED=True`.

En local, le plus simple est de mettre `CELERY_TASK_ALWAYS_EAGER=True` dans le `.env` : les tâches s'exécutent en synchrone dans le process Django, sans avoir besoin de Redis ni d'un worker. Sans cette variable, il faut lancer Redis et un worker Celery :

```bash
# Redis
brew install redis
brew services start redis

# Worker Celery (dans un terminal séparé)
uv run celery -A conf worker --loglevel=info
```

En tests, les tâches sont forcées en mode eager et le SDK Brevo est mocké (cf. `conftest.py`) — aucun appel réseau n'est effectué.

## Import des établissements

Le formulaire de demande d'atelier utilise la table `School` pour proposer une recherche d'établissement par nom ou code postal.

Les établissements sont importés depuis le jeu de données `fr-en-annuaire-education` de `data.education.gouv.fr`, en excluant les écoles. L'import est idempotent : relancer la commande met à jour les établissements existants à partir de leur identifiant unique.

```bash
uv run python manage.py import_schools
```

La commande utilise la variable d'environnement `HUWISE_API_KEY` pour appeler l'API. En local, renseigner cette clé dans `.env` avant de lancer l'import.

Les noms d'établissements sont aussi stockés dans une version normalisée sans accents (`name_normalized`) afin de permettre une recherche accent-insensitive dans le formulaire.

## Déploiement (Scalingo)

### Serveur web (Gunicorn)

Le nombre de workers et de threads est configurable via des variables d'environnement, à définir dans le dashboard Scalingo pour chaque application :

| Variable | Staging | Prod |
|---|---|---|
| `GUNICORN_WORKERS` | `1` | `3` |
| `GUNICORN_THREADS` | `2` | `4` |

Ces valeurs sont lues par `gunicorn.conf.py` à la racine du projet.

