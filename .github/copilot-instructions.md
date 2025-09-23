# Copilot Instructions for AI Coding Agents

## Project Overview
- **Backend**: Django REST Framework (DRF) with hexagonal/microservice-inspired architecture, in `BACK_FormContainers/`.
- **Frontend**: Next.js (TypeScript), in `FRONT_FormContainers/`.
- **Data**: SQLite for dev, Dockerized for deployment, Excel for some data imports.

## Key Architectural Patterns
- **Hexagonal (Ports & Adapters)**: Core logic in `app/domain/` (entities, rules, ports), application services in `app/application/`, infrastructure in `app/infrastructure/`.
- **API Layer**: DRF ViewSets and manual endpoints in `app/interfaces/`.
- **Celery**: For async/background tasks (`core/celery.py`).
- **Swagger/OpenAPI**: `/api/docs/` via drf_spectacular.

## Developer Workflows
- **Build/Run (Backend)**:
  - Use Docker: see `command.md` for up/down/build commands.
  - Local: `python manage.py runserver` (env vars via `.env`).
- **Tests**: `pytest` (see `pytest.ini`).
- **Migrations**: `python manage.py makemigrations` / `migrate`.
- **Custom Commands**: In `app/management/commands/` (see `dedup_actores.py` for argument patterns).
- **Frontend**: `npm run dev` in `FRONT_FormContainers/`.

## Project-Specific Conventions
- **API URLs**: Always end with `/` unless noted. Some manual endpoints allow optional trailing slash.
- **Auth**: Admin and user tokens managed via cookies/localStorage. See `lib/api.admin.ts` and `lib/api.panel.ts` for helpers.
- **Questionnaire Import/Export**: JSON structure enforced in admin UI (`src/app/admin/page.tsx`).
- **Business Rules**: Centralized in `app/domain/rules.py`.
- **Data Normalization**: Use provided helpers for plates, seals, containers, etc.

## Integration Points
- **Frontend↔Backend**: API proxied via Next.js rewrites (`next.config.ts`).
- **External Services**: Google credentials via env, see `core/settings.py`.
- **Docs**: See `docs/README.md` for architecture, deployment, and user management details.

## Examples
- To add a new business rule: implement in `app/domain/rules.py`, expose via service in `app/application/services.py`, wire to API in `app/interfaces/`.
- To add a new admin API: add endpoint in DRF ViewSet, update `lib/api.admin.ts` and UI in `src/app/admin/`.

## References
- [docs/README.md](../BACK_FormContainers/docs/README.md)
- [command.md](../BACK_FormContainers/command.md)
- [core/settings.py](../BACK_FormContainers/core/settings.py)
- [app/domain/rules.py](../BACK_FormContainers/app/domain/rules.py)
- [lib/api.admin.ts](../FRONT_FormContainers/lib/api.admin.ts)
- [next.config.ts](../FRONT_FormContainers/next.config.ts)

---
For unclear or missing conventions, check the `docs/` folder or ask for clarification.
