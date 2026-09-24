---
name: django-architecture
description: >
  Thin architecture-routing adapter for Django backends — confirms the
  project is genuinely Django, routes greenfield vs. existing work to the
  right entry point, and maps the framework-agnostic three-zone model
  (core/modules/shared) onto Django's app-based structure. Deliberately
  thin: no Django naming-convention, data-layer, testing, or bootstrap
  specialist skills exist yet in this plugin — this skill says so and asks
  rather than inventing them. Use when the user says things like "structure
  my Django app", "where does this Django code belong", "set up a Django
  project", or "how should I organize this Django codebase".
---

# Django Architecture (thin adapter)

This skill exists so a Django task reliably lands on *something* in this
plugin instead of falling through to nothing, or to advice borrowed from the
FastAPI adapter (Django's own conventions — apps, models, the ORM — differ
enough from FastAPI's that a direct copy would mislead). It is intentionally
minimal — a routing layer over the framework-neutral model, not a Django
specialist. Deeper Django-specific skills (module scaffolding, naming, data
layer, testing, bootstrap) are future work, not yet written.

## Step 0: Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo before checking anything below
yourself. If that plugin isn't installed, fall through to Step 1's own live
check.

## Step 1: Detect the stack

Look for `manage.py` at the project root, or `django` in
`requirements.txt`/`pyproject.toml`. Also note whether Django REST Framework
(`djangorestframework`) is present — a plain Django app serving HTML
templates and a DRF-based API need different advice for where "the API"
even lives.

If none of these resolve and the user wants a new service, confirm Django is
actually the intended framework rather than assuming it from "Python
backend" alone — FastAPI is this plugin's other, much deeper-covered option.

## Step 1a: Check for an existing structure that predates this plugin

If the project already has existing Django apps not scaffolded by this
plugin, route to a sibling `architecture-foundations` plugin's
`existing-codebase-adoption` skill first — it decides whether Kaizen's
conventions or the existing structure govern before anything below gets
applied. If genuinely greenfield, skip to Step 2 — routing through a sibling
`architecture-foundations` plugin's `project-kickoff` skill for the
sequencing if this is the very start of a new project (there is no
`django-project-bootstrap` skill yet — say so plainly and use
`django-admin startproject`/`startapp` as the starting point).

## Step 2: Map Django's own structure onto the three zones

Django already organizes code into "apps," which is a coarser unit than this
suite's per-domain `modules/` folder, but the underlying mapping still holds:

- **`core/`** → the Django *project* package (`settings.py`, root
  `urls.py`, `wsgi.py`/`asgi.py`) plus any cross-cutting middleware. Imported
  by the entrypoint; contains no business logic.
- **`modules/`** → each Django *app* that represents one business domain
  (e.g. a `products` app, an `orders` app) — Django already calls these
  "apps," which is the same concept as this suite's "module," just Django's
  own name for it. Don't rename them to `modules/products/` when Django's
  own `products/` app convention (with its own `models.py`, `views.py`,
  `urls.py`, `serializers.py` if DRF is present) already serves the same
  purpose — the zone mapping is what matters, not forcing Django into this
  suite's folder names. Apps should still avoid importing each other's
  internals directly; if two need to share something, that's a signal for
  Step 3 below or a dedicated shared app.
- **`shared/`** → a dedicated shared/common Django app, or a top-level
  `shared/` package, for zero-business-logic reusables (base model mixins,
  generic pagination, formatting helpers).

Django's ORM models sit where the FastAPI adapter's `infra/` repository
layer would — don't assume a repository-pattern abstraction over the ORM is
wanted just because the FastAPI adapter uses one; Django's `Model` classes
and querysets are a different, equally valid persistence style, and
introducing a repository layer on top is a choice to ask about, not a
default.

## Step 3: What this skill does not yet cover

There is no Django-specific naming-convention, data-layer, testing, or
bootstrap skill in this plugin. Don't invent app-splitting rules, DRF
serializer conventions, or testing setup patterns as if they were
established convention — ask the user what they'd like, or point at the
closest neutral guidance (`architecture-foundations`'s `test-pyramid` skill
still applies, since it's concept-level, not stack-specific).

## Step 4: Never assume

Per the `working-agreement` skill's rule 4: this adapter is thin by design,
so silent defaults here are more likely to be wrong than on the FastAPI
adapter. Check for existing project documentation first, and ask before
assuming Django REST Framework, a particular auth backend, or a
repository-over-ORM pattern the project hasn't already committed to.

---
_Last reviewed: 2026-08-24_
