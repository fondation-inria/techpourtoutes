.PHONY: help install dev test lint format icons

help:
	@echo "Available targets:"
	@echo "  install  Install dependencies"
	@echo "  dev      Start dev server with Tailwind watcher"
	@echo "  test     Run tests"
	@echo "  lint     Lint with ruff"
	@echo "  format   Format with ruff"
	@echo "  icons    Build SVG icon sprite"

install:
	uv sync --group dev

server:
	uv run python manage.py tailwind runserver

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

icons:
	uv run python manage.py build_svg_sprite
