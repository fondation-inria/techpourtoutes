.PHONY: help install sync run test lint format pre-commit icons seed

DB_NAME = techpourtoutes

help:
	@echo "Available targets:"
	@echo "  install      First-time project setup (DB, .env, deps, migrations, seed)"
	@echo "  sync         Install or update dependencies and run migrations"
	@echo "  run          Start dev server with Tailwind watcher"
	@echo "  test         Run tests"
	@echo "  lint         Lint with ruff"
	@echo "  format       Format with ruff"
	@echo "  pre-commit   Manually run all pre-commit hooks"
	@echo "  icons        Build SVG icon sprite"
	@echo "  seed         Seed database with minimal dev data"

install:
	uv sync --group dev
	@createdb $(DB_NAME) 2>/dev/null \
		&& echo "  Database $(DB_NAME) created." \
		|| echo "  Database $(DB_NAME) already exists, skipping."
	@if [ -f .env ]; then \
		echo "  .env already exists, skipping."; \
	else \
		cp .env.example .env; \
		sed -i '' "s|postgres://username@|postgres://$(shell whoami)@|" .env; \
		echo "  .env created (DATABASE_URL configured for user: $(shell whoami))."; \
	fi
	uv run python manage.py migrate
	uv run pre-commit install
	uv run python manage.py seed

sync:
	uv sync --group dev
	uv run python manage.py migrate

run:
	uv run python manage.py tailwind runserver

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

pre-commit:
	uv run pre-commit run --all-files

icons:
	uv run python manage.py build_svg_sprite

seed:
	uv run python manage.py seed
