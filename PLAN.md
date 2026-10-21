# Social Fossils implementation roadmap

## Goal and planning assumptions

Complete the current Telegram analytics product, then introduce orchestration,
broader platform support, and deployment infrastructure in that order. Keep
import and analytics business logic independently runnable and testable; Airflow
and Kubernetes are later operational layers, not prerequisites for local use.

Decisions confirmed for this plan:

- Treat every imported Telegram account as an account belonging to the same
  owner. The product-wide analytics scope is the combined owner, not a
  user-selected account.
- Make that combined scope visible in the dashboard and preserve source-account
  provenance for debugging and optional breakdowns.
- Merge contact identities only when their normalized Telegram user IDs match.
  Do not infer identity from display names. Keep unidentified senders scoped to
  their source account.
- The Communication Timeline uses monthly UTC buckets over all available
  history by default.

## Current project state

The repository already contains:

- A FastAPI/SQLAlchemy backend and PostgreSQL schema for Telegram accounts,
  contacts, chats, members, messages, and import sessions.
- A Telegram JSON parser and idempotent command-line importer.
- Overview, chat, sender/contact, and communication-balance analytics APIs.
- A Forgotten Contacts API with inactivity/decline calculations, evidence
  indicators, monthly activity, ranking, and limits, plus a combined-owner
  dashboard with ranked contacts, evidence status, and activity comparisons.
- A React dashboard with overview, chats, contacts, and communication-balance
  sections and frontend/backend tests.
- A local Docker Compose setup for frontend, backend, PostgreSQL, and Adminer.

The remaining Phase 3 gap is the Communication Timeline endpoint and UI.
Existing analytics other than Forgotten Contacts currently aggregate across
accounts without a common canonical contact identity. There is no Airflow DAG,
additional platform importer, or Kubernetes deployment configuration. The
README's roadmap/TODO is behind the implemented features and should be updated
as roadmap work lands.

Relevant existing code includes `backend/app/models.py`,
`backend/app/importer.py`, `backend/app/routers/analytics.py`,
`backend/app/schemas/analytics.py`, `backend/tests/test_analytics.py`,
`frontend/src/App.tsx`, `frontend/src/api.ts`, and
`frontend/src/components/`.

## Recommended order and rationale

Move the account-scope foundation ahead of the two new dashboard surfaces.
Both Forgotten Contacts and Timeline need reliable aggregation across accounts;
implementing those screens first would either duplicate account logic or expose
misleading account-local results. The revised Phase 3 order is:

1. Establish combined-owner and cross-account contact identity semantics.
2. Build the Forgotten Contacts dashboard on the existing API, updating the API
   to use the combined-owner scope.
3. Add the Communication Timeline API.
4. Build the Communication Timeline dashboard.

The following phases remain in their requested order. Production container
standardization in Kubernetes Phase 6 should harden and separate the existing
Compose setup rather than recreate local Docker support that already exists.

## Phase 3: Complete the analytics product

### 3a. Combined-owner scope (replaces account selection)

**Backend and data model**

- Treat all currently imported Telegram accounts as belonging to the one
  product owner; avoid introducing account selection or an implicit
  all-versus-one toggle.
- Add the smallest schema-backed canonical identity mapping needed to unify
  contacts across source accounts. A canonical identity is keyed by platform
  and normalized platform user ID; source account/contact rows remain intact
  and attributable.
- Keep contacts without a reliable Telegram user ID account-local. Never merge
  by name, username, or chat title.
- Add the required Alembic migration and migration tests. Preserve existing
  uniqueness constraints and data; do not rewrite existing imports or messages
  merely to create a merged view.
- Consolidate analytics around a shared owner-wide query/scope. Apply the same
  scope to overview, chats, contacts, communication balance, forgotten
  contacts, and timeline; ensure counts do not accidentally duplicate a
  message when identities are linked across accounts.
- Expose source-account attribution in results where it is useful, and show a
  clear “combined account data” scope label in the UI. Avoid displaying
  sensitive message contents.

**Verification**

- Test two accounts with the same peer Telegram ID: the peer is presented as
  one identity, while counts include each account's messages exactly once.
- Test different Telegram IDs with the same display name: they remain separate.
- Test null/unknown sender IDs: they are not falsely linked across accounts.
- Verify all existing analytics return the combined-owner scope and preserve
  correct message totals, owner direction, and per-source provenance.
- Test migration from the current schema without data loss and test an empty
  database.

### 3b. Forgotten Contacts dashboard

- Add TypeScript response types and an API client for
  `/api/analytics/forgotten-contacts`; update the API contract for combined-owner
  aggregation and canonical contact identity.
- Add a dashboard section with ranked contacts, inactivity duration,
  historical-versus-recent monthly activity, and decline indicators. Clearly
  distinguish inactive, declining, active, and insufficient-evidence results.
- Show the API summary counts and evidence status; explain that classifications
  are descriptive heuristics, not judgments about relationships.
- Provide useful search/sort behavior and explicit loading, retry/error,
  no-import, no-eligible-contact, no-match, and insufficient-history states.
- Keep the layout accessible and responsive and do not render message text.

**Verification:** frontend component/API tests for ranking, filtering,
classification/evidence labels, empty/loading/error/retry states, and combined
owner data; backend tests for canonical identity aggregation and all existing
Forgotten Contacts heuristics.

### 3c. Communication Timeline API

- Define a documented response schema for monthly UTC buckets over all available
  history. Return message counts by month, owner/contact direction where
  reliable, active-day context, and unknown/ambiguous direction separately.
- Provide an owner-wide timeline and the data needed to inspect a canonical
  contact's timeline. Keep the selected identity and provenance explicit.
- Use ordinary messages for communication trends; do not silently count service
  events as user-written communication. Do not invent events for missing
  timestamps or infer direction when identity/direction is ambiguous.
- Use stable month labels and return zero-activity months between the earliest
  and latest relevant dated messages so gaps and renewed activity are visible.
- Implement as reusable analytics/service logic called from the API, with
  bounded/efficient SQL aggregation rather than moving business logic into
  route handlers. Reuse the common owner scope and canonical identity mapping.

**Verification:** endpoint/schema tests for month boundaries in UTC, sparse
history, zero-activity gaps, unknown timestamps/directions, service messages,
account aggregation, and contact-specific data. Include SQL dialect coverage
supported by the existing test setup.

### 3d. Communication Timeline dashboard

- Add typed API client and a responsive timeline view for monthly activity.
- Visualize gradual decline, sudden silence, and renewed activity without
  labeling an absence as a relationship judgment. Include separate direction
  series only when direction is reliable.
- Support owner-wide and canonical-contact views, clear date/month labels,
  empty/error/loading states, and accessible non-visual summaries.
- Prefer a small native SVG/CSS visualization consistent with existing
  dependencies; add a chart dependency only if the required interaction cannot
  be delivered reliably without one.

**Verification:** frontend tests for plotted/summarized values, gaps, decline
and renewal patterns, direction uncertainty, contact selection, accessibility
labels, and loading/error/empty states.

## Phase 4: Introduce Airflow

Keep all parsers, import operations, normalization, and analytics in reusable
application modules. Airflow DAGs should orchestrate those functions rather
than contain business logic. Keep the present Compose/local workflow functional
without an Airflow scheduler.

### 16. Design a repeatable data-processing pipeline

- Identify idempotent stages and explicit task dependencies: discover/validate
  export, import raw records, normalize identities, compute analytics, and
  report outcome.
- Define DAG parameters, ownership of temporary files, concurrency limits, and
  how a run identifies its input and target owner.
- Document local execution of each processing service without Airflow.

### 17. Extract and validate new data

- Wrap the existing Telegram parser/importer in callable services and add a
  validated pipeline entry point.
- Record task/run linkage and statuses using current import-session records or
  a justified additive model/migration; do not duplicate status storage without
  a clear need.
- Keep private export contents and message text out of logs.

### 18. Normalize imported data

- Make normalization callable and deterministic outside a DAG.
- Preserve raw imported payloads and source provenance; make retries safe.
- Validate normalization behavior with synthetic multi-account and
  identity-conflict fixtures.

### 19. Recompute derived analytics

- Define which analytics are computed on demand versus materialized/recomputed.
- Add a reusable recomputation service only for metrics that need it; avoid
  redundant derived tables before measured performance justifies them.
- Make a rerun idempotent and scoped to the intended owner/data range.

### 20. Add retry and failure handling

- Configure task-level retry policies for transient failures and no retry for
  invalid input/data errors.
- Preserve transaction boundaries and report final failure accurately.
- Test retries, partial failures, rollback, and safe reruns.

### 21. Add pipeline monitoring and history

- Surface run status, start/end time, duration, task failure, and safe error
  summaries.
- Link orchestration runs to import-session records without exposing personal
  message data.
- Add operational tests for success, failure, and missing/invalid input.

### 22. Schedule periodic processing

- Add schedules only after an input-discovery mechanism and retention policy
  exist; do not schedule repeatedly against a mutable personal export path
  without defined semantics.
- Keep scheduling configurable and disabled or inert in the basic local
  workflow unless explicitly enabled.

**Phase 4 exit criteria:** DAGs run against the production application services,
retries do not duplicate imported data, task history is inspectable, and the
importer/analytics services remain independently testable and runnable.

## Phase 5: Expand the data platform

### 23. Add more messaging platforms

- Select one platform based on export availability and data quality before
  building its importer.
- Implement platform-specific parsing behind the existing import-service
  boundary; retain platform source IDs and raw payloads.
- Add synthetic fixtures, parser validation, idempotency, and importer tests.

### 24. Normalize identities across platforms

- Extend canonical identity mapping to include platform-specific identifiers
  and explicit, auditable links between identities where the same person uses
  different IDs across platforms.
- Do not infer cross-platform identity from names or contact-book position.
- Include conflict and unlink behavior before cross-platform aggregates are
  enabled.

### 25. Build cross-platform communication analysis

- Add analytics only after identity mapping has reliable, testable semantics.
- Preserve source platform and owner/contact direction as dimensions; define
  which totals can safely be compared across platforms.
- Verify no duplicate counting when one conversation or identity is linked
  across sources.

### 26. Add more expensive or precomputed analytics

- Profile the owner-wide analytics before adding materialized or cached
  results.
- Define refresh/invalidation behavior for imports and identity changes.
- Use PostgreSQL and Airflow only where measured query cost or refresh needs
  justify them.

### 27. Handle larger exports and incremental ingestion

- Measure import/query bottlenecks with representative synthetic large data.
- Add streaming/chunked parsing or bulk upsert paths where evidence supports
  them; preserve transaction safety, import-session counts, and uniqueness.
- Define checkpoints and retry semantics for incremental imports, and verify
  full re-import remains safe.

**Phase 5 exit criteria:** at least one additional importer works through the
same reusable pipeline, identity links are explicit, combined analytics retain
provenance, and incremental processing is safe to retry.

## Phase 6: Introduce Kubernetes

Do this only after the application and pipeline boundaries stabilize. Existing
Docker Compose remains the local development path.

### 28. Containerize and standardize application services

- Harden/standardize the existing backend and frontend images for production
  use: deterministic builds, non-root execution where practical, minimal
  runtime contents, and explicit health/readiness behavior.
- Preserve Compose service names, local mounts, and local startup behavior.

### 29. Separate development and production configuration

- Separate development defaults from production secrets/configuration.
- Validate required variables at startup and document secret injection; never
  commit credentials or bake them into images.

### 30. Deploy the FastAPI backend

- Add Kubernetes Deployment/Service configuration with externalized config,
  resource requests/limits, non-root security settings, and readiness/liveness
  probes.
- Keep database connectivity configured through the environment and a
  Kubernetes Secret.

### 31. Deploy the frontend

- Choose Kubernetes hosting or static hosting based on operational needs.
- Configure the API base URL per environment and verify browser access,
  CORS, and release compatibility.

### 32. Deploy and configure Airflow

- Deploy only the DAGs and scheduler/executor components needed by the
  established pipeline.
- Configure persistent logs/metadata, secrets, workers/resources, and
  restricted access; keep local Airflow optional.

### 33. Configure persistent database storage and backups

- Define PostgreSQL ownership, persistent storage, backup cadence, retention,
  restore procedures, and recovery verification before production data is
  stored.
- Prefer a managed PostgreSQL service if it meets deployment requirements;
  avoid assuming a local Compose volume is a production backup.

### 34. Add health checks, resource limits, and monitoring

- Add probes and resource bounds for backend, frontend (if hosted in cluster),
  and Airflow.
- Monitor service health, database connections/storage, DAG failures, and
  request latency without logging private content.

### 35. Automate deployments

- Add CI/CD after images and deployment configuration are reproducible.
- Build/test images, scan dependencies/images with approved tooling, deploy
  through an environment-specific promotion path, and document rollback.

**Phase 6 exit criteria:** production services have externalized secrets,
working probes, persistence and tested backups, observable processing runs,
and a repeatable release/rollback path; local Compose remains straightforward.

## Cross-cutting implementation and test rules

- Keep HTTP concerns in FastAPI, import/business logic in reusable Python
  services, and presentation logic in React.
- Follow existing SQLAlchemy/Alembic patterns. Any schema evolution must be
  additive, migrated, and tested against existing data.
- Use synthetic data only in committed tests; never commit real Telegram
  exports.
- Protect privacy: do not log or render message contents; keep diagnostics and
  pipeline errors useful without exposing personal data.
- Validate backend unit/API tests and frontend tests/build after each coherent
  feature. Run migrations against a disposable database and test current
  Compose startup when infrastructure changes.
- Update README roadmap and local run instructions when the implementation
  order or supported workflow changes.

## Suggested delivery slices

1. Combined-owner model, migration, analytics scope, and cross-account tests.
2. Forgotten Contacts API scope update and dashboard.
3. Timeline contract, query/service, and API tests.
4. Timeline visualization and frontend tests/build.
5. Airflow design and reusable service adapters, then DAG/retry/history/schedule.
6. Additional importer and identity/cross-platform analytics.
7. Production container/configuration work, then Kubernetes deployment and CI/CD.
