# Tech Pour Toutes

Plateforme web Django pour la communauté Tech Pour Toutes.

## Stack technique

- **Python 3.14** / **Django 6**
- **uv** pour la gestion des dépendances
- **PostgreSQL**
- **Ruff** pour le linting et le formatage
- **Tailwind CSS** + **DaisyUI** (via django-tailwind-cli)
- **django-cotton** pour les composants UI

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


## Tester les emails en local

En développement (`DEBUG=True`), Django envoie les emails via SMTP sur `localhost:1025`. [Mailpit](https://mailpit.axllent.org/) intercepte ces emails et les affiche dans une interface web.

> La connexion des mentors passe par un lien magique envoyé par email — Mailpit est donc **nécessaire** pour s'authentifier en local.

```bash
# Installer Mailpit
brew install mailpit
# to run automatically in the background
brew services start mailpit
# or to run it manually
mailpit
```

L'interface est disponible sur [http://localhost:8025](http://localhost:8025). Tous les emails envoyés par l'application y apparaissent.

> En production, les emails sont envoyés via [Brevo](https://www.brevo.com/) (Anymail). La variable `BREVO_API_KEY` doit être renseignée dans le `.env`.

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
