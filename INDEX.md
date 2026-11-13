# Project index

Social Fossils imports messaging exports and presents analytics about accounts,
chats, contacts, and messages. This page is a navigation map for contributors
and coding agents; see [README.md](README.md) for the quick-start instructions.

## System at a glance

```text
Browser (React) -> FastAPI upload API -> staged file + UploadJob -> Airflow DAG
                                                             -> platform importer
PostgreSQL <- SQLAlchemy models and import/analytics services
Browser <- FastAPI analytics and identity-link APIs
```

Uploads are staged in a shared Compose volume so the backend and Airflow can
read the same file. Airflow coordinates the import; parsing and persistence
logic live in backend services so they remain separate from the DAG.

## Where things live

| Path | Purpose |
| --- | --- |
| `docker-compose.yml` | Local app stack: frontend, API, PostgreSQL, Airflow, and Adminer. |
| `backend/app/` | FastAPI application, database layer, SQLAlchemy models, parsers, importers, and analytics routes. |
| `backend/app/main.py` | Creates the FastAPI app, middleware, and API routers. |
| `backend/app/routers/` | HTTP endpoints for uploads, analytics, and cross-platform identity links. |
| `backend/app/parsers/` | Convert Telegram, Instagram, Facebook, and VK exports into normalized parsed data. |
| `backend/app/importers/` | Persist parsed exports and import-session results; `import_utils.py` contains shared import helpers. |
| `backend/app/constants.py` | Shared platform, parsing, import, and analytics constants, including platform upload configuration. |
| `backend/app/routers/analytics_*.py`, `backend/app/schemas/analytics_*.py` | Analytics API endpoints and domain-specific response schemas; `backend/app/routers/analytics.py` composes the analytics router. |
| `backend/app/models.py`, `backend/app/db.py`, `backend/app/config.py` | Database schema, SQLAlchemy setup, and application settings. |
| `backend/alembic/` | Alembic migration environment and schema history; `backend/alembic.ini` configures migrations. |
| `backend/tests/` | Backend tests for parsers, importers, API routes, analytics, and migrations. |
| `airflow/dags/import.py` | Validates staged uploads, calls the backend importer, and records job completion/failure. |
| `airflow/entrypoint.sh` | Airflow container startup helper. |
| `frontend/src/` | React app, dashboard views/components, hooks, API client, and frontend tests. |
| `frontend/src/App.tsx`, `frontend/src/main.tsx` | Dashboard shell and frontend bootstrap. |
| `frontend/src/api.ts`, `frontend/src/types.ts`, `frontend/src/platforms.ts` | Backend requests, API data types, and supported upload platforms. |
| `frontend/src/components/`, `frontend/src/hooks/` | Dashboard UI and reusable data/filter/upload state. |
| `frontend/package.json`, `vite.config.ts`, `Dockerfile` | Frontend scripts, Vite configuration, and container build. |
| `.env.example`, `backend/requirements.txt`, `frontend/package-lock.json` | Environment template and dependency manifests. |

## Main request and data flow

1. The frontend sends an export and platform to `backend/app/routers/upload.py`.
2. The API validates the type, writes the file to the configured staging
   directory, creates an `UploadJob`, and triggers the Airflow DAG through
   `backend/app/airflow_client.py`.
3. `airflow/dags/import.py` validates the staged job and calls
   `import_source_export` from `backend/app/importers/telegram_importer.py`;
   platform configuration routes to the Telegram, Instagram, Facebook, or VK
   importer.
4. The importer uses a platform parser and SQLAlchemy models to store accounts,
   chats, contacts, messages, and import status in PostgreSQL.
5. Analytics routers query that data; the frontend API client and dashboard
   hooks load it into the views under `frontend/src/components/`.

## Working conventions

- Treat `backend/app/models.py` and the existing migrations as the schema
  source of truth. Make schema changes through Alembic migrations.
- Keep HTTP handling in routers, platform parsing/import logic in backend
  services, and orchestration in the Airflow DAG.
- Use synthetic export data in tests. Real messaging exports are private and
  should not be committed.
- Run the local stack with `docker compose up --build -d`; Compose starts the
  API, frontend, database, and Airflow services.
- Backend tests: `cd backend && pytest`. Frontend tests: `cd frontend && npm test`.
