# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Behavioral guidelines

1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

    State your assumptions explicitly. If uncertain, ask.
    If multiple interpretations exist, present them - don't pick silently.
    If a simpler approach exists, say so. Push back when warranted.
    If something is unclear, stop. Name what's confusing. Ask.

2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

    No features beyond what was asked.
    No abstractions for single-use code unless specifically asked for.
    No "flexibility" or "configurability" that wasn't requested.
    No error handling for impossible scenarios.
    If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

3. Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

    Don't "improve" adjacent code, comments, or formatting.
    Don't refactor things that aren't broken.
    Match existing style, even if you'd do it differently.
    If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

    Remove imports/variables/functions that YOUR changes made unused.
    Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

4. Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

    "Add validation" → "Write tests for invalid inputs, then make them pass"
    "Fix the bug" → "Write a test that reproduces it, then make it pass"
    "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Commands

```bash
# Install dependencies
uv sync --group dev

# Run dev server with Tailwind watcher
uv run python manage.py tailwind runserver

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Build SVG icon sprite (after adding icons to ui/svg_source/)
uv run python manage.py build_svg_sprite
```

## Architecture

Django 6 + PostgreSQL project. Locale is French (fr-FR), timezone Europe/Paris.

**Key directories:**
- `api/`
- `conf/` — Django project settings and root URLs
- `techpourtoutes/` — main Django app (views, models, templates, URLs)
- `ui/` — design system app: cotton components, static files, SVG management

### Backend

**Core entities:**
- `User` -

**Relationships:**

**Audit trail:** `django-simple-history` middleware is active — models that need history tracking should use `HistoricalRecords`.

### Frontend

**Frontend stack:** Tailwind CSS via `django-tailwind-cli` + DaisyUI components. Pre-commit automatically rebuilds Tailwind on HTML/CSS changes. Alpine.js + HTMX for interactivity

**Component system:** `django-cotton` components live in `ui/templates/cotton/`. Layout components (base, sidebar, footer) are in `ui/templates/cotton/layout/`; UI primitives (button, card, badge, icon, etc.) are in `ui/templates/cotton/components/`. Use these components by composing `<c-layout.base>`, `<c-button>`, etc. in templates.

**SVG icons:** Source SVGs go in `ui/svg_source/`. Running `build_svg_sprite` compiles them into a sprite at `ui/static/svg/`. Reference icons via the `<c-icon>` cotton component.

## Code Conventions

- Ruff with line length 99, Django rules (DJ), PEP8 (E/W), logic (F), and import sorting (I)
- Always use double quotes for strings
- When a method becomes complex, extract into well-named private methods for readability
- Use mixins, custom Managers / QuerySets and utility modules to isolate behavior (equivalent of Basecamp style with concerns in Rails)
- Service objects for procedural logic with success/failure states (sequential actions, external calls)
- Keep models and views lean
- Comments only for code that is truly difficult to understand (avoid unnecessary comments)
- Do not reference AI tools (Claude, Cursor, etc.) in code, comments, or commits
- Avoid unnecessary guard clauses and intermediate variable assignments
- Prefer native framework solutions over custom implementations
