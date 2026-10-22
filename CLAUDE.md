# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Behavioral guidelines

### 1. Think before coding

Don't assume. Don't hide confusion. Surface tradeoffs. Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity first

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code unless specifically asked for.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical changes

Touch only what you must. Clean up only your own mess.

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it unless asked.
- Remove the imports, variables, functions, templates, tests and icons that YOUR changes made unused.

The test: every changed line should trace directly to the user's request.

### 4. Test-driven development

Write the failing test first. Always. For every feature, fix, or behaviour change:

1. Write a test that fails for the right reason — extend or edit an existing test if the behaviour fits there, create a new one only if it doesn't. Verify it fails before writing any implementation.
2. Write the minimum implementation to make it pass.
3. Run the full test suite to check for regressions.

Exceptions:

- Pure template/UI changes with no logic: state explicitly why no test is needed.
- Removing a behaviour: remove the tests that described it, and adjust the ones that relied on it in passing.

### 5. Goal-driven execution

Define success criteria. Loop until verified. Turn tasks into verifiable goals — "add validation" → "write tests for invalid inputs, then make them pass"; "fix the bug" → "write a test that reproduces it, then make it pass"; "refactor X" → "tests pass before and after". For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]

### 6. Git is the user's

Never touch the index or the history without an explicit instruction: no `git add`, `git rm`, `git mv`, `commit`, `push`, `stash`, `reset`, `checkout`, `restore`, `merge`, `rebase` or branch change. Delete, move and edit files with plain file operations, and leave every change unstaged for the user to review.

## Commands

Every make target wraps `uv`. Never run `python manage.py` without `uv run`.

```bash
make install    # first-time setup: DB, .env, deps, migrations, pre-commit hooks, seed
make sync       # install/update deps + run migrations
make run        # dev server with Tailwind watcher
make test       # whole suite with coverage, browser tests included (~1 min 40)
make test-fast  # no browser tests, no coverage (~50 s)
make lint       # ruff check
make format     # ruff format
make icons      # rebuild the SVG sprite — run it after any change in ui/svg_source/, commit the sprite
make seed       # seed DB with minimal dev data (idempotent)
```

Seed creates: one `Pro` with superuser role — `admin@techpourtoutes.io` / `admin` — one `Beneficiary` with a `TrainingExperience` — `beneficiary@techpourtoutes.io` / `beneficiary` — and 16 approved upcoming `Event`s covering every subcategory but `OTHER`, so every card colour and the pagination show up. When `SEED_TEAM_EMAILS` is set (review apps), it replaces those two accounts with, for each address, an adult student, a minor pupil and an admin pro as `+etudiante` / `+lyceenne` / `+pro` aliases, the pro sharing `SEED_ADMIN_PASSWORD`; the events then belong to the first of these pros. Every login or email-change code is `FIXED_VERIFICATION_CODE` when set (`111111` in `.env.example`) — honoured only under `DEBUG`. It also imports the Onisep samples committed under `data/onisep/` (~100 coherent rows per file) rather than downloading the full datasets.
One file or one test: `uv run pytest <path>[::<test>] -q --no-cov` — coverage is in `addopts`, so drop it with `--no-cov` when iterating.

## Architecture

Django 6 + PostgreSQL. Locale is French (fr-FR), timezone Europe/Paris.

**Key directories:**

- `conf/` — Django settings and root URLs
- `techpourtoutes/` — main Django app (views, models, services, templates, URLs, tests)
- `techpourtoutes/clients/` — thin HTTP client wrappers (httpx-based)
- `ui/` — design system app: cotton components, static files, SVG management

### Two sites in one

The same app serves two audiences. The beneficiaries' site lives at `/` (`urls_beneficiary.py`), the coalition's — the pros — under `/coalition/` (`urls_coalition.py`); `urls_common.py` holds what both share (auth, account, static pages, search). A page belongs to the coalition when its URL name is in `urls_coalition`: the `is_coalition_page` tag (`templatetags/coalition_page.py`) reads that to pick the sidebar and the favicon. The old `coalition.techpourtoutes.io` host is redirected onto `/coalition/…` by `middleware.coalition_host_redirect`.

### Backend

**BaseModel:** all models inherit from `techpourtoutes/models/base.py`: UUID primary key, `created_at`/`updated_at`, and `full_clean()` called automatically on save.

**Core entities:**

- `User` — custom user model (`AUTH_USER_MODEL`), extends `AbstractUser` via `BaseModel`; carries the identity shared by both audiences (civility, phone, postal code, Jobirl ids). Passwordless: the login is a 6-digit code mailed by `issue_login_code()` (15 min, limited attempts) and checked by `consume_login_code()`. A one-hour magic link (`issue_login_token()` / `consume_login_token()`, route `login_verify`) only survives in the mail asking a pro to modify her event. Auth views live in `views/auth_views.py`. `soft_delete()` anonymises rather than deletes.
- `Pro` — multi-table inheritance from `User`. Adds `structure_type` (`Pro.StructureType`; `Pro.WITHOUT_STRUCTURE` lists the retired and jobless answers, who have no structure name), `structure_name`, `job_title` and `engagements` (an array of `Pro.Engagement`). Password is unusable.
- `Beneficiary` — multi-table inheritance from `User`. Adds `birth_date` (always given at sign-up, nullable only because `soft_delete()` blanks it), the legal representative asked of a minor joining the mentoring, and `has_requested_training_ambassador`. Password is unusable.
- `School` — every établissement referenced by Onisep, secondary and higher-ed alike (~20 000). Identified by `onisep_id`; `uai` and `siret` are **not** unique in the source. Two independent flags (`secondary`, `higher_ed`) say which file(s) it came from — ~4 000 are in both — plus `training_ambassador_eligible` for the training ambassador list. Search relies on the accent-free `name_normalized` / `acronym_normalized`.
- `Formation` — a diploma or curriculum as referenced by Onisep (~5 900), independent of where it is taught. `exit_level` uses the shared `Level` enum. Its `secondary`/`higher_ed` flags are derived one hop away: from the scope (`lycee`/`superieur`) of the `FormationAction` rows linking to it, not from the formation's own Onisep file.
- `FormationAction` — the through model linking a `Formation` to a `School` (~70 700). Onisep gives each link its own id, and the same pair can carry several, so only `onisep_id` is unique.
- `TrainingExperience` — one parcours, i.e. one school year of one user. `school` and `formation` are nullable because the catalogue does not hold everything: what the user typed then lands in `out_of_scope_school_name` / `out_of_scope_formation_name`. A `CheckConstraint` per side enforces **exactly one** of the two, so `school_label` / `formation_label` always have something to display. Writing one side blanks the other (`TrainingExperienceFormMixin.save_training`).
- `Level` (`models/level.py`) — the study levels shared by `TrainingExperience` and `Formation.exit_level`. `TrainingExperience.LEVELS` is the subset the beneficiary funnel offers; the extra members (CAP, bac +6 to +9) only describe imported formations.
- `WorkshopRequest` — one row per workshop type requested by a `Pro`, with an optional shared remark.
- `Event` — one event submitted by a `Pro`, moderated in the admin (`status` pending / approved / rejected, tracked by `HistoricalRecords`). `subcategory` holds either a `Subcategory` value or the free text typed when none fits, so `category` is not a column: it is derived through the `SUBCATEGORIES` map — free text lands where `OTHER` does — and drives `category_color`, the colour of the card. A `CheckConstraint` enforces that an event ends after it starts. `EventQuerySet` composes `approved()`, `upcoming()` (one that has started but not ended is still to come), `past()`, `in_category()` / `in_subcategory()`.
- `SavedEvent` — one event a `Beneficiary` put aside, unique per pair. `SavedEvent.objects.toggle(event=…, beneficiary=…)` deletes the row or creates it, and returns whether the event is now saved.

**Relationships:**

- `Pro` and `Beneficiary` inherit from `User` (multi-table inheritance — one DB row per table).
- `WorkshopRequest` belongs to `Pro` (`pro.workshop_requests`); `Event` too (`pro.events`).
- `Formation` and `School` are many-to-many through `FormationAction` (`formation.schools`, `school.formations`).
- `TrainingExperience` points at a single `School` with `on_delete=SET_NULL`, so re-importing never destroys a user's parcours.
- `Event` and `Beneficiary` are many-to-many through `SavedEvent` (`event.saved_by`, `beneficiary.saved_events`).

**Onisep imports:** `import_schools_and_formations` is the master command — it chains the school, formation, action, ambassador-flag, recommendation-flag and Carif-Oref steps in that order. It runs with `--if-empty --sample` in the Procfile `postdeploy` (a fresh review app gets the committed samples, already-populated staging/prod are a no-op), and monthly through `cron.json` (Scalingo scheduler) with `--async` — that pass is the real import.

The work is split across three layers of services, and the commands own none of it:

- `services/onisep_api/fetch_{schools,formations,formation_actions}.py` — the only code that hits the network. Each holds its own Onisep dataset ids and goes through `OnisepApiBaseService.request()` (`clients/onisep.py`, no API key).
- `services/<domain>/import_*.py` — the only code that decides where records come from: a committed sample (`--sample`) or a download. Sample filenames are derived from the périmètre (`{prefix}_{scope}_sample.csv`), read through `utils/onisep.read_onisep_csv`. Sample headers are the Onisep JSON keys, so both paths run the same mapping code.
- `services/<domain>/upsert_*.py` — mapping and `bulk_create(update_conflicts=True)`. That bypasses `save()` — hence the `*_normalized` columns computed in the mapper — and each scope excludes the other's flags from `update_fields` so a school listed in both files keeps both.

`--sample` says *which data*, `--async` says *where it runs*. With `--async` the master command enqueues a Celery `chain` of one task per step (`tasks/import_onisep_*.py`), so a transient Onisep failure is retried and a definitive one reaches Sentry through `CeleryIntegration`. `--if-empty` is rejected in that mode: the sub-commands are bypassed, so nobody carries the guard. On the synchronous path the commands log at ERROR before raising `CommandError`, which Django turns into `sys.exit()` — invisible to Sentry otherwise.

**Service objects:** inherit from `BaseService` (`services/base.py`). Implement `perform(**kwargs)`; call `self.fail("message")` to signal failure. Check `result.success` / `result.failure` and `result.errors` at the call site. A failure also carries an `ErrorKind` (`PERMANENT` by default, `TRANSIENT` when the same call could succeed later), read through `result.failed_with_transient_error`. `fail_with_errors(result)` relays another service's failure — its messages and its kind — which is how an orchestrator stays a plain `BaseService`.

They are filed in two kinds of package: one per external API (`brevo_api/`, `carif_oref_api/`, `geoplateforme_api/`, `jobirl_api/`, `n8n_api/`, `onisep_api/`) holding only the code that talks to it, and one per model or business domain (`account/`, `beneficiary/`, `contact/`, `event/`, `formation/`, `formation_action/`, `pro/`, `school/`, `storage/`) for everything else — including orchestrators that call an API service. Only `base.py` and `base_api.py` sit at the root.

**`BaseApiService`** (`services/base_api.py`) extends `BaseService` for the services that actually talk to an external API, and for those only — an orchestrator that merely relays their failure (`ImportSchools`, `SyncBrevoContact`, `UpsertManifesteSignatory`…) stays a `BaseService`. Subclasses set `status_code` / `network_error` from the response and then fail as usual: the kind is never declared by hand, it is derived from what came back (no answer, 429, 5xx ⇒ `TRANSIENT`). The service says what the failure *was*; the Celery task decides what to do with it, through `raise_failure(result)` (`tasks/_retry.py`), which picks between `TransientError` and `RuntimeError`.

**Mailers:** `techpourtoutes/mailers/`, one `BaseMailer` subclass per module (`AccountMailer`, `AuthMailer`, `BeneficiaryMailer`, `ConsortiumMailer`, `PerfectibleMailer`, `ProMailer`). Each `@classmethod` calls `send_mail`, which renders the `.txt` + `.html` pair named after **the calling method**, in the folder named after the class (`ProMailer.welcome` → `emails/pro/welcome.{txt,html}`). Every subject carries `EMAIL_SUBJECT_PREFIX`, derived at boot from Scalingo's `$APP` by `utils/environment.email_subject_prefix`: `[staging] ` on staging, `[pr-320] ` on a review app, nothing in production or in local dev.

**Jobirl integration:** external mentoring platform. Services live in `services/jobirl_api/`. Use `JobirlApiBaseService` (extends `BaseApiService`) — it wraps `JobirlClient` (`clients/jobirl.py`) and exposes `result.jobirl_response_body` (the `datas` key of the response) on success. A mentor's `situation_pro` is derived from her `structure_type`.

**n8n workshop notifications:** workshop requests notify Latitudes through `NotifyWorkshopRequest` (`services/n8n_api/`), over `LatitudesN8nClient` (`clients/n8n.py`); webhook URL and basic auth come from the `N8N_WORKSHOP_WEBHOOK_*` settings. Calls run through the Celery task `notify_workshop_request_task`, which retries transient failures via `tasks/_retry.py`.

**Brevo contact sync:** gated globally by `settings.BREVO_SYNC_ENABLED` (default `False` — off in local/dev, on in prod) and per instance by `User.brevo_sync_enabled`. `signals.connect_brevo_sync(model_cls)`, called for `Pro` and `Beneficiary` in `apps.py`, connects `post_save` (upsert) and `pre_delete` (delete) handlers, which schedule Celery tasks on `transaction.on_commit` when both flags are on. The tasks call `UpsertBrevoContact` / `DeleteBrevoContact` (`services/brevo_api/`) over `BrevoClient` (`clients/brevo.py`). Field-to-attribute mapping and per-model list resolution are in `services/brevo_api/mappings.py`; a choice field is sent as the list of its labels (`BREVO_MULTIPLE_CHOICE_FIELDS`), so the Brevo attribute must be a multiple choice with those very labels.

**Async tasks (Celery):** app in `conf/celery.py`, broker Redis (`REDIS_URL`). Set `CELERY_TASK_ALWAYS_EAGER=True` to run tasks without a worker; the root `conftest.py` does so for the whole suite and mocks the Brevo SDK — no Brevo/Redis access from tests.

**Feature switches:** `django-waffle`. A switch is created by a data migration, gates views with `@waffle_switch` and templates with `{% switch %}`, and is forced in tests with `override_switch`. On a review app, `/deploy-review-app ACTIVE_SWITCHES=a,b` turns switches on (`review-app.yml`). Once a feature is out for everyone, remove the switch, the code of its "off" branch, and the switch row through a migration.

**Forms:** plain `forms.Form` with a manual `save()`, not `ModelForm` (the admin aside). Preferred because forms rarely map 1:1 to a model (several models, or fields like `terms_accepted` that belong to none).

**Views:** function-based views only.

**View naming:** `<action>_<resource>`, where the action is the Rails REST verb — `index`, `show`, `new`, `create`, `edit`, `update`, `destroy`: `index_events`, `show_pro_training_experience`, `edit_user`, `destroy_beneficiary_training_experience`. Two extra actions cover what REST has no single word for:

- `upsert_<resource>` — one view that both creates and updates.
- `show_<resource>_form` — one view that renders both the `new` and the `edit` form.

The URL name matches the view name, so `reverse()` and the function are one word apart.

**One route, one view.** Two `path()` entries never share a function, and no view branches on `request.method`: a form is two routes, `edit_user` (GET) rendering it and `update_user` (POST) saving it, `new_event` (GET) and `create_event` (POST) likewise. What the pair has in common goes into a private helper — `new_beneficiary_training_experience` and `create_beneficiary_training_experience` both call `_render_beneficiary_training_experience_form`.

Endpoints serving a partial name the partial as their resource: `destroy_user_modal`, `show_skip_beneficiary_inscription_step_modal`.

Exceptions are rare — static pages (`static_views`, `home`…), `search_views`, `robots_views`, the `login_*` views, the funnels (`beneficiary_inscription_funnel`, `pro_inscription_funnel`). Think thoroughly before diverging from the convention, and always say so.

**Templates take the name of the view that renders them** — and when a route was split in two, that is always the GET half: `edit_pro_training_experience` and `update_pro_training_experience` both render `account/partials/edit_pro_training_experience.html`. Modals follow the rule too (`destroy_user_modal.html`). The partials a view merely composes into its page are named for what they show (`account/partials/show_username.html`, `pro_cards.html`).

**Inscription funnel:** `beneficiary_inscription_funnel` keeps the answers in the session, never in the browser, through the shared `utils/funnel.py`: `FunnelSteps` says which screens follow which (optional ones shown only when an answer asks for them), `FunnelSession` stores each screen's answers under one session key, forgotten after an hour without activity. Every POST carries its own screen only; it is validated against `answers_with(step, posted)` and saved only once valid, and the GET renders the step she reached directly. A screen is only accepted once every active screen before it is saved: otherwise the funnel expired or was started over from another tab, and she is sent to the first missing screen with a message saying so. Every link into the funnel goes through `new_beneficiary_inscription_funnel` (`/inscription/new/`), which starts over, records what she came for (`wants_mentor`, `wants_training_ambassador`, `saved_event`) and redirects to `beneficiary_inscription_funnel` (`/inscription/`): reloading that URL resumes, coming back through a button starts afresh. Creating the account re-binds every form from the session — the safety net for an answer gone stale meanwhile — then clears it, as do the dead-ends.

**Pro inscription funnel:** `pro_inscription_funnel` (`/coalition/inscription/`, entered through `new_pro_inscription_funnel?engagement=…`, which pre-checks that engagement) runs on the same `utils/funnel.py`. Its optional screens are shown by predicates over the chosen engagements (`FunnelSteps.optional` accepts a callable): `training_ambassador` and `workshop_request` for their own engagement, `additional_information` for any other — events only count when chosen alone. A training ambassador may only add events (`ProEngagementsForm.clean`, mirrored by the `lock` of `checkbox_group`). `events` and `other` are offered alongside the engagements without being `Pro.Engagement`s: the first, chosen alone, sends her to `index_pro_events` after the code, the second's message is mailed to the team and never stored. `ProAdditionalInformationForm` takes the workshop answers: when she works at that school, it neither asks again nor lets her change what the workshop screen already said. The checkboxes are kept whole through `FunnelSession(multiple=…)`, and the workshop form carries a `workshop` prefix, since every screen's answers land in one merged dict. `CreatePro` writes the pro and every engagement's side effects; the welcome mail carries the login code.

**Adding an engagement:** a button asks `pro_engagement_action` (`templatetags/pro_engagements.py`, whose docstring holds the button to copy) whether to link to `new_pro_engagement`, post straight to `create_pro_engagement` — nothing left to give — send a mentor to her mentoring space, show it disabled with the reason as a tooltip (a beneficiary, a pro who may not take it on), or show nothing (an engagement already taken on, but sponsorship and workshops which may be given again; `mobilize_structure` once signed in). `new_pro_engagement` sends a visitor to the inscription funnel and shows a pro the one screen she still has to answer (`utils/pro_engagement_screens.screen_for`); `ProAdditionalInformationForm(pro=…)` only asks what her profile lacks, the rest waiting in `form.known`. Eligibility lives in `CheckProEngagementEligibility` alone: `AddProEngagement` runs it first, the views never do. A failure sends her back to `next`, the page she clicked from, kept only when it is on the site. `CreatePro` and `AddProEngagement` share `ProEngagementMixin`.

**Workshop request flow:** the `workshop_request` screen (`ProWorkshopRequestForm`), in the pro inscription funnel or through `new_pro_engagement`, gives the pro the `workshops` engagement; `ProEngagementMixin` persists one `WorkshopRequest` per selected workshop type and enqueues the n8n notification task. The chosen school's **UAI** is not stored on the `Pro`: it is a form-only field (`structure_uai`) handed to the task alongside the workshop types, and reaches Latitudes as `identifiant_etablissement`.

**Events listing:** `index_events` lists the approved upcoming events, `EVENTS_PER_PAGE` at a time. Whether the visitor already bookmarked an event is annotated on the queryset (`Exists`), never fetched per card, so the page costs the same number of queries whatever the number of events. Who gets which bookmark is decided once, by `_bookmark_action`, and the card knows nothing but that word: a beneficiary posts to `update_saved_event`, which swaps the button with the partial of the same name; an anonymous visitor opens `create_saved_event_modal`, inviting her to join the club; a signed-in pro gets no bookmark at all. Paging is the shared `<c-components.pagination>` component, fed by the `elided_pages` filter (`templatetags/pagination.py`) because the eliding arguments cannot be passed from a template.

**School autocomplete:** one endpoint, `search_schools`, parameterised by a `scope` query param. `views/search_views.py` holds the `SCOPES` registry, where each scope decides four things: which subset of `School` it searches, whether a numeric token matches the postal code, the ordering, and the template rendering one row of the dropdown. Adding a périmètre means adding an entry, not a view. The single cotton component is `ui/templates/cotton/components/form_fields/school_search.html`; its `key` var says whether the selected school's UUID or its UAI lands in the hidden id field.

**Formation autocomplete:** `search_formations`, scoped the same way through its own `FORMATION_SCOPES` registry (`secondary`/`higher_ed`, matching `Formation.secondary`/`higher_ed`), further narrowed to a selected school's catalogue via `FormationQuerySet.taught_at`. The cotton component is `formation_search.html`; every template pairs it with a `school_search` block, passing it the same `scope` literal so a level that only offers secondary schools only ever offers secondary formations. `TrainingExperienceFormMixin.resolve_formation` (`forms/mixins/training_experience_form_mixin.py`) enforces the same scoping server-side, including the établissement-not-found fallback.

**Object storage:** any S3-compatible provider (currently OVHcloud) through `django-storages[s3]`; buckets, provider setup and review apps are in `infra/object_storage/README.md`. In the code:

- `STORAGES` has a private `default` (its `url()` is presigned for 5 minutes) and a `public` one (unsigned, cacheable URLs). A model field targets the public bucket with `storage=` a callable returning `storages["public"]`.
- Files never go through the app: `CreatePresignedUpload` (`services/storage/`) signs a PUT the browser sends straight to the bucket, whose signed headers (exact `Content-Length`, checked against a maximum before signing, `Content-Type`, ACL, `Cache-Control`) the bucket enforces. The key is a UUID under a prefix, never the client's filename.
- Without `S3_PRIVATE_BUCKET` (local dev, tests) both storages fall back to the disk, and the same PUT is signed by Django (`utils/local_upload.py`) and received by `create_local_upload`, which enforces the same policy.
- A private file is never linked by its presigned URL — it expires — but by an app route that checks permissions and redirects to a freshly signed one.
- Tests use the `s3_storages` fixture (moto), which does **not** enforce signed headers: assert on the signed URL (`X-Amz-SignedHeaders`) instead.

**Audit trail:** `django-simple-history` middleware is active — models that need history tracking use `HistoricalRecords`.

### Frontend

**Stack:** Tailwind CSS via `django-tailwind-cli` + DaisyUI. Pre-commit rebuilds Tailwind on HTML/CSS changes. Alpine.js + HTMX for interactivity.

**Component system:** `django-cotton` components live in `ui/templates/cotton/`: layout components (base, email, partials) in `layout/`, UI primitives (button, card, badge, icon…) in `components/`, larger compositional patterns in `patterns/`. A file `foo_bar.html` is used as `<c-components.foo-bar>` or `<c-components.foo_bar>`.

**SVG icons:** source SVGs go in `ui/svg_source/`. `build_svg_sprite` (`make icons`) compiles them into `ui/static/svg/sprite.svg`, and `<c-components.icon name="…">` points a `<use>` at that sprite **as an external file**; `variant="image"` shows `static/images/<name>.webp` instead. The script redraws the icons as plain centred strokes at half the width so none depends on a clip-path (the Penport exports create bold-rendering bugs on Firefox). The `codex-*` letters keep a `clipPath`, but it only repeats a crop their `viewBox` already applies.

## Code conventions

- Ruff with line length 99, Django rules (DJ), PEP8 (E/W), logic (F), and import sorting (I). Double quotes.
- Human-readable code: the top-level function reads like prose, the mechanics pushed into well-named private helpers (see `_on_user_saved` and its `_schedule_contact_upsert` / `_contact_was_previously_synced` helpers in `signals.py`).
- Mixins, custom Managers / QuerySets and utility modules isolate behaviour (Basecamp-style concerns); service objects hold procedural logic with success/failure states. Keep models and views lean.
- Avoid unnecessary guard clauses and intermediate variables. Prefer native framework solutions over custom ones.
- Comments only for code that is truly hard to understand.
- Docstrings and comments are in English. Only what the user sees is in French: CLI output, argument `help`, validation messages, `verbose_name`, templates and emails.
- User-facing French is written in the feminine (the site explains why on `pourquoi_nous_ecrivons_au_feminin`): « inscrite », « une mentore », « ta date de naissance ». Pros are addressed with « vous », beneficiaries with « tu ». In templates, French typography puts `&nbsp;` before `: ; ! ?`.
- Do not reference AI tools (Claude, Cursor, etc.) in code, comments, or commits.

## Testing

- `pytest` with `@pytest.mark.django_db` for any test touching the database; Django's `client` fixture and `reverse()` for view tests.
- No factory_boy — plain model instantiation or pytest fixtures.
- Imports go at the top of the test module, not inside the test, unless the test needs the patched object an import inside a `with patch(…)` returns.
- Mails land in `django.core.mail.outbox` without any setting: pytest-django already switches to the locmem backend.
- Name a view's tests after the view: `test_update_user_valid_saves_and_returns_info_card`, not `test_account_edit_...`.
- A data migration is tested in `tests/migrations/test_<migration>.py`. When its function only needs today's models, import it with `importlib` and call it with `django.apps.apps` (see `test_0061_…`); when it reads a column the migration then removes, migrate with `MigrationExecutor` to the state before it (see `test_0062_…`).

### Test layout

`techpourtoutes/tests/` mirrors the app package, one directory per source directory.

**One source file, one test file, matching name.** `services/brevo_api/upsert_contact.py` is tested by `tests/services/brevo_api/test_upsert_contact.py` — never a grab-bag `test_services.py`. `ui/tests/` mirrors the `ui` app the same way. Both apps are listed in `testpaths`.

A few tests have no single source file and stay at the root of `tests/`: `test_seo.py` (meta/og tags in the base template), `test_urls.py` (route conventions, legacy redirects), `test_error_pages.py` (403/404 handlers), `test_collectstatic.py` (the production static storage). Shared helpers sit there too: `birth_dates.py` (`birth_date_for_age`), `sitemap_exclusions.py`.

### Fixtures

- `techpourtoutes/tests/conftest.py` — available everywhere: `pro`, `beneficiary`, `school`, `higher_ed_school`, `formation`, `higher_ed_formation`, `experience`, `beneficiary_experience`, `event`, `moderator_pro` / `event_moderator_group`, `inactive_user`, `valid_pro_model_data`, `s3_storages`, `mock_geocoding`, plus `school_record` / `formation_record` / `formation_action_record` / `carif_oref_record`, builders returning one source row with its real keys.
- Directory-level `conftest.py` for fixtures shared within one directory only (`tests/admin/conftest.py`, `tests/services/brevo_api/conftest.py`). Don't promote a fixture to the root `conftest.py` until a second directory needs it.
- The root `conftest.py` (project root, not `tests/`) holds autouse fixtures for the whole suite: in-memory cache, simple static storage (no manifest), eager Celery, mocked Brevo SDK.

### End-to-end tests

`tests/e2e/` drives a real browser via `pytest-playwright` against `live_server`, with shared steps in `tests/e2e/helpers.py`. Browsers are not installed by `make install` — run `uv run playwright install chromium` once, otherwise those tests error out on a missing binary. `make test-fast` leaves them out.
