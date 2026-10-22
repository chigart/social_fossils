# Social Fossils — Copilot Instructions

## Project overview

Social Fossils analyzes personal messaging history to understand communication
patterns, relationships, and changes in social interactions over time.

The first data source is a Telegram JSON export.

## Technology stack

### Application
- Backend: Python, FastAPI, SQLAlchemy 2.
- Database: PostgreSQL.
- Migrations: Alembic.
- Frontend: React, TypeScript, Vite.

### Data pipelines and orchestration
- Apache Airflow: workflow orchestration and scheduling of data processing
  pipelines.
- Keep ingestion and data processing logic independent of Airflow so it can
  be tested and executed without an Airflow scheduler.

### Infrastructure
- Docker: application containerization.
- Docker Compose: the complete local application and Airflow workflow.

### Development environment
- VS Code running locally on the host.
- The application must run locally using `docker compose up --build`.
- Do not require VS Code Dev Containers.

Do not introduce additional frameworks, services, or dependencies unless they
solve a concrete problem and are justified.
Airflow is part of the default local Compose workflow for upload-triggered
processing. Do not introduce Kubernetes or production deployment components.

## Architecture

- Keep HTTP/API concerns in the FastAPI application.
- Keep Telegram parsing and import logic separate from API route handlers.
- Keep database access consistent with the existing SQLAlchemy setup.
- Keep frontend code separate from backend code.
- Use the existing PostgreSQL database and SQLAlchemy models.
- Do not duplicate business logic between the frontend and backend.
- Prefer small, focused modules and functions over large monolithic files.
- The product is single-owner and local-only: do not add app registration,
  login, or authorization. Keep service ports bound to localhost.

## Database rules

The existing PostgreSQL schema and SQLAlchemy models are implemented and
working. Treat them as the source of truth.

- Inspect existing models before writing database-related code.
- Reuse existing tables, columns, indexes, and constraints.
- Do not recreate or redesign the schema without an explicit requirement.
- Do not modify Alembic migrations merely to work around application bugs.
- If a schema change becomes necessary, explain why before implementing it.
- Use database constraints and PostgreSQL conflict handling to maintain
  uniqueness and data integrity.
- Use SQLAlchemy sessions and explicit transaction boundaries.
- Handle transaction rollback and failure reporting correctly.

## Telegram importer

The initial input file is `data/result.json`.

The export contains `personal_information`, `contacts`, and `chats` sections.

### Identity and relationships

- Read the account owner's ID from `personal_information.user_id`.
- Normalize user IDs consistently. The owner's numeric ID may appear in
  message records as a string prefixed with `user`.
- Do not confuse user IDs, chat IDs, and message IDs.
- Use the existing database uniqueness constraints for chats, contacts,
  and messages.
- Do not invent identifiers or infer identity from display names.
- Telegram address-book contacts may lack Telegram user IDs. Do not link
  them to sender records without reliable identifying information.

### Messages

- Support both ordinary messages and service messages.
- Preserve service events rather than silently discarding them.
- Distinguish service events from ordinary user-written messages in analytics.
- Support Telegram's `text` field as either a string or a list of entities.
- Preserve the original message object in `raw_payload`.
- Use `date_unixtime` as the preferred timestamp source.
- Store timestamps in UTC when they can be interpreted reliably.
- Do not guess timezones for ambiguous timestamps.
- Determine outgoing status by comparing the normalized sender ID with the
  account owner's ID, not by comparing names.
- Use `NULL` when outgoing status cannot be determined.

### Idempotency and import sessions

- Re-importing an export must not create duplicate messages.
- Use PostgreSQL `ON CONFLICT` handling for database uniqueness.
- Do not overwrite existing messages unless an explicit update policy is
  implemented.
- Record import status, timestamps, message counts, and errors using the
  existing `import_sessions` table.
- Ensure failed imports are reported accurately.
- Make transaction boundaries explicit and support safe retries.

## Docker and development workflow

- The application must run through Docker Compose.
- The intended startup command is `docker compose up --build`.
- Services communicate using their Compose service names.
- The backend connects to PostgreSQL using the configured `DATABASE_URL`.
- Inside Docker, the database hostname is `db`, not `localhost`.
- Do not require VS Code Dev Containers.
- Do not require Node.js on the host to run the application in Docker.
- If host-side tooling is useful, keep it optional.
- `docker compose up --build` must apply application migrations and start the
  complete app without a separate setup command.
- Keep database files, Airflow metadata/logs, and staged exports ephemeral;
  use RAM-backed staging shared by the backend and Airflow. Do not mount real
  Telegram exports from the host.

## Code quality

- Follow existing project conventions before introducing new ones.
- Use Python type hints.
- Prefer clear names and straightforward implementations.
- Avoid unnecessary abstractions, premature optimization, and speculative
  features.
- Handle expected errors explicitly.
- Do not silently swallow exceptions.
- Avoid broad exception handling unless needed to preserve transaction
  integrity or provide useful error reporting.
- Do not hardcode credentials, machine-specific paths, or environment-specific
  configuration.
- Use environment variables for configuration and secrets.
- Never log message contents, phone numbers, credentials, or other sensitive
  personal data unnecessarily.

## Testing and verification

- Add tests for new parsing and database behavior.
- Test malformed input and missing optional fields.
- Test repeated imports and duplicate handling.
- Test outgoing-message classification.
- Test failure handling and transaction rollback.
- Prefer isolated unit tests for parsing and normalization.
- Do not claim code is tested unless the tests were actually executed.
- Do not make unrelated changes while implementing a specific feature.

## Data privacy and Git

- Treat Telegram exports and message contents as private personal data.
- Do not commit real Telegram exports or other personal messaging data.
- Keep `data/result.json` out of version control.
- Do not expose personal message content in logs, test fixtures, or examples.
- Use synthetic data in committed tests.

## Airflow

- Use Airflow for orchestration, scheduling, retries, and monitoring of
  multi-step data pipelines.
- Keep business logic in independently testable Python modules, not inside
  DAG definitions.
- DAGs should call reusable application services rather than implement
  ingestion or transformation logic themselves.
- Make tasks idempotent where possible so retries do not create duplicate data.
- Define task dependencies explicitly.
- Do not introduce Airflow merely to execute a simple one-off local command.
- Follow the Airflow version and configuration already present in the project.

## Working approach

Before implementing a task:

1. Inspect the relevant existing files.
2. Identify the smallest change that satisfies the requirement.
3. Follow the current architecture and database schema.
4. Implement the change.
5. Run relevant tests or checks.
6. Summarize changed files and verification results.
7. Identify unresolved assumptions or limitations.

Do not rewrite working components without a clear reason.
Do not add features outside the requested scope.
If a requirement conflicts with the existing schema or architecture, explain
the conflict instead of silently redesigning the project.
Never commit to git.
Never edit README.md.