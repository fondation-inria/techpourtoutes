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


4. Test-Driven Development

Write the failing test first. Always.

For every feature, fix, or behaviour change:

1. Write a test that fails for the right reason — extend or edit an existing test if the behaviour fits there, create a new one only if it doesn't. Verify it fails before writing any implementation.
2. Write the minimum implementation to make it pass
3. Run the full test suite to check for regressions

Do not write implementation code before a test exists.

Exceptions:
- pure template/UI changes with no logic. In that case, state explicitly why no test is needed.
- if you remove some behaviour, think of removing the associated unused tests


5. Goal-Driven Execution

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

All make commands are aliasing uv commands. Never run python manage.py without uv run
```bash
make install  # first-time setup: DB, .env, deps, migrations, pre-commit hooks, seed
make sync     # install/update deps + run migrations
make run      # dev server with Tailwind watcher
make test     # run tests
make lint     # ruff check
make format   # ruff format
make icons    # rebuild SVG sprite
make seed     # seed DB with minimal dev data (idempotent)
```

Seed creates: one `Pro` with superuser role — `admin@techpourtoutes.io` / `admin`.

## Architecture

Django 6 + PostgreSQL project. Locale is French (fr-FR), timezone Europe/Paris.

**Key directories:**
- `conf/` — Django project settings and root URLs
- `techpourtoutes/` — main Django app (views, models, services, templates, URLs, tests)
- `techpourtoutes/clients/` — thin HTTP client wrappers (httpx-based)
- `ui/` — design system app: cotton components, static files, SVG management

### Backend

**BaseModel:** All models inherit from `techpourtoutes/models/base.py`. Provides UUID primary key, `created_at`/`updated_at` timestamps, and calls `full_clean()` automatically on save (validation before every write).

**Core entities:**
- `User` — extends Django's `AbstractUser` via `BaseModel`. Custom user model (`AUTH_USER_MODEL`). Uses passwordless email-link login: `issue_login_token()` generates a hashed token with a 1h TTL; `consume_login_token(plaintext)` validates and invalidates it atomically. Auth views live in `techpourtoutes/views/auth_views.py`.
- `Pro` — multi-table inheritance from `User`. Adds civility, birth date, phone, job title, personal address, optional structure fields, and Jobirl integration fields (`jobirl_user_id`, `jobirl_user_token`). Password is set to unusable on creation.
- `School` — imported education institutions used by the workshop request form. Stores the official identifier, display name, normalized accent-free name for search, and postal code. Populate it with `uv run python manage.py import_schools`; the command fetches `data.education.gouv.fr` using `HUWISE_API_KEY`, excludes schools, and upserts by identifier.
- `WorkshopRequest` — one row per workshop type requested by a `Pro`, with an optional shared remark. The workshop landing form can create multiple rows from one submission.

**Relationships:**
- `Pro` inherits from `User` (Django multi-table inheritance — one DB row per table).
- `WorkshopRequest` belongs to `Pro` through `pro.workshop_requests`.

**Service objects:** Inherit from `BaseService` (`techpourtoutes/services/base.py`). Implement `perform(**kwargs)`; call `self.fail("message")` to signal failure. Check `result.success` / `result.failure` and `result.errors` at the call site.

**Mailers:** `techpourtoutes/mailers.py` — class-based, no inheritance. Each mailer exposes `@classmethod` methods that call `send_mail` with rendered txt+html templates (`CoalitionUserMailer`, `CoalitionInternalMailer`, `AuthMailer`).

**Jobirl integration:** External mentoring platform. Services live in `techpourtoutes/services/jobirl_api/`. Use `JobirlApiBaseService` (extends `BaseService`) for requests — it wraps `JobirlClient` (`techpourtoutes/clients/jobirl.py`) and exposes `result.jobirl_response_body` (the `datas` key from the response) on success.

**n8n workshop notifications:** Workshop requests notify Latitudes through `NotifyWorkshopRequest` in `techpourtoutes/services/n8n_api/`, which dispatches HTTP calls through `LatitudesN8nClient` (`techpourtoutes/clients/n8n.py`). The webhook URL comes from `N8N_WORKSHOP_WEBHOOK_URL`; basic auth comes from `N8N_WORKSHOP_WEBHOOK_BASIC_AUTH_USER` and `N8N_WORKSHOP_WEBHOOK_BASIC_AUTH_PASSWORD`. Calls run through the Celery task `notify_workshop_request_task`, which retries transient failures (network errors, HTTP 429, and 5xx responses) using the shared retry behavior in `techpourtoutes/tasks/_retry.py`.

**Brevo contact sync:** Gated globally by `settings.BREVO_SYNC_ENABLED` (env `BREVO_SYNC_ENABLED`, default `False` — off in local/dev, on in prod). Also gated per-instance by `User.brevo_sync_enabled`. `techpourtoutes/signals.py` connects `post_save` (upsert) and `pre_delete` (delete) handlers via `connect_brevo_sync(model_cls)` — called once per syncable subclass (e.g. at the bottom of `pro.py`). Handlers short-circuit when either flag is off; otherwise they schedule Celery tasks on `transaction.on_commit`. Tasks live in `techpourtoutes/tasks/` and call services in `techpourtoutes/services/brevo_api/` (`UpsertBrevoContact`, `DeleteBrevoContact`), which use `BrevoClient` (`techpourtoutes/clients/brevo.py`). Field-to-attribute mapping and per-model list resolution are in `services/brevo_api/mappings.py`.

**Async tasks (Celery):** Celery app lives in `conf/celery.py`. Broker is Redis (`REDIS_URL`). In tests and (optionally) local dev, set `CELERY_TASK_ALWAYS_EAGER=True` to run tasks synchronously without a worker. The root `conftest.py` enforces eager mode and mocks the Brevo SDK for the whole test suite — no Brevo/Redis access from tests.

**Forms:** Use plain `forms.Form` with a manual `save()`, not `ModelForm`. Preferred when the form doesn't map 1:1 to a model (e.g. spans multiple models, or includes fields like `terms_accepted` that belong to no model).

**Views:** Function-based views only.

**Workshop request flow:** `workshops_landing` uses `WorkshopForm`, creates a `Pro` with the `workshops` engagement, persists one `WorkshopRequest` per selected workshop type, sends the welcome email, and enqueues the n8n notification task. `search_schools` returns an HTMX partial for the school autocomplete; search is token-based and accent-insensitive via `School.name_normalized`.

**Audit trail:** `django-simple-history` middleware is active — models that need history tracking should use `HistoricalRecords`.

### Frontend

**Frontend stack:** Tailwind CSS via `django-tailwind-cli` + DaisyUI components. Pre-commit automatically rebuilds Tailwind on HTML/CSS changes. Alpine.js + HTMX for interactivity

**Component system:** `django-cotton` components live in `ui/templates/cotton/`. Layout components (base, email, partials) are in `ui/templates/cotton/layout/`; UI primitives (button, card, badge, icon, etc.) are in `ui/templates/cotton/components/`; larger compositional patterns are in `ui/templates/cotton/patterns/`. Use these components by composing `<c-layout.base>`, `<c-button>`, etc. in templates.

**SVG icons:** Source SVGs go in `ui/svg_source/`. Running `build_svg_sprite` compiles them into a sprite at `ui/static/svg/`. Reference icons via the `<c-icon>` cotton component.

## Code Conventions

- Ruff with line length 99, Django rules (DJ), PEP8 (E/W), logic (F), and import sorting (I)
- Always use double quotes for strings
- Favour human-readable code: the top-level function should read like prose, with the mechanics pushed into well-named private helpers (see `_on_user_saved` and its `_schedule_contact_upsert` / `_contact_was_previously_synced` helpers in `techpourtoutes/signals.py`)
- When a method becomes complex, extract into well-named private methods for readability
- Use mixins, custom Managers / QuerySets and utility modules to isolate behavior (equivalent of Basecamp style with concerns in Rails)
- Service objects for procedural logic with success/failure states (sequential actions, external calls)
- Keep models and views lean
- Comments only for code that is truly difficult to understand (avoid unnecessary comments)
- Do not reference AI tools (Claude, Cursor, etc.) in code, comments, or commits
- Avoid unnecessary guard clauses and intermediate variable assignments
- Prefer native framework solutions over custom implementations

## Testing

- Use `pytest` with `@pytest.mark.django_db` for any test touching the database
- Use Django's built-in `client` fixture for view tests; use `reverse()` for URLs
- No factory_boy — use plain model instantiation or pytest fixtures
- Shared fixtures for techpourtoutes app live in `techpourtoutes/tests/conftest.py`: `mentor`, `valid_pro_data`, `valid_pro_model_data`, `mock_register_mentor_on_jobirl`
- The root `conftest.py` has an autouse fixture that swaps static file storage (no manifest required in tests)
