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
  templates/
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
```

## Lancer le projet en développement

Il faut deux processus : le serveur Django et le watcher Tailwind. Les deux peuvent tourner ensemble avec la commande

```bash
uv run python manage.py tailwind runserver
```

Le premier lancement installera Tailwind CSS CLI si nécessaire.
L'application est disponible sur [http://localhost:8000](http://localhost:8000).


## Tester les emails en local

En développement (`DEBUG=True`), Django envoie les emails via SMTP sur `localhost:1025`. [Mailpit](https://mailpit.axllent.org/) intercepte ces emails et les affiche dans une interface web.

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

```bash
# Lancer les tests
uv run pytest

# Linter
uv run ruff check . # commande lancée automatiquement avant chaque commit

# Formateur
uv run ruff format . # commande lancée automatiquement avant chaque commit

# Lancer les hooks pre-commits manuellement
uv run pre-commit run --all-files
```


## Icônes SVG

Les icônes sont regroupées dans un sprite SVG généré automatiquement.

**Ajouter une icône :**

1. Déposer le fichier `.svg` dans `ui/svg_source/` — le nom du fichier devient l'identifiant de l'icône (ex. `mon-icone.svg`).
2. Rebuilder le sprite :

```bash
uv run python manage.py build_svg_sprite
```

Le sprite est écrit dans `ui/static/svg/sprite.svg`.

**Utiliser une icône dans un template :**

```html
<c-components.icon name="mon-icone" class="size-6" />
```

Le composant cotton `ui/templates/cotton/icon.html` génère un `<svg><use>` qui pointe vers le sprite.
