# Social Fossils implementation roadmap

## Goal and planning assumptions

Phases 1–4 are complete. The target product is a single-owner local app that
starts with `docker compose up --build`. Keep import and analytics business
logic independently runnable and testable; Airflow orchestrates the local
upload workflow but is not a dependency of the core services or CLI. There is
no Social Fossils account system, and personal app data is ephemeral.

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
- The application has no login or authorization. Its services are exposed only
  on localhost, and imported data is held in ephemeral container/RAM-backed
  storage. Airflow retains its separate local UI account.
- Kubernetes and production deployment are out of scope.

## Current project state

The repository already contains:

- A FastAPI/SQLAlchemy backend and PostgreSQL schema for Telegram accounts,
  contacts, chats, members, messages, and import sessions.
- A Telegram JSON parser and idempotent command-line importer, plus an
  Instagram JSON archive importer using the shared upload pipeline.
- Overview, chat, sender/contact, and communication-balance analytics APIs.
- A Forgotten Contacts API with inactivity/decline calculations, evidence
  indicators, monthly activity, ranking, and limits, plus a combined-owner
  dashboard with ranked contacts, evidence status, and activity comparisons.
- A React dashboard with overview, chats, contacts, and communication-balance
  sections and frontend/backend tests.
- A local Docker Compose setup for frontend, backend, PostgreSQL, Adminer, and
  the Airflow upload pipeline.

Phases 1–4, including combined-owner analytics, Forgotten Contacts, the
Communication Timeline, and per-file upload-triggered Airflow processing, are
considered complete. The upload/job API is single-owner and unauthenticated.
The Instagram importer is the first Phase 5 data-source expansion. Further
cross-platform identity, analytics, and scaling work remains future scope.
There is no Kubernetes deployment configuration.

Relevant existing code includes `backend/app/models.py`,
`backend/app/telegram_importer.py`, `backend/app/routers/analytics.py`,
`backend/app/schemas/analytics.py`, `backend/tests/test_analytics.py`,
`frontend/src/App.tsx`, `frontend/src/api.ts`, and
`frontend/src/components/`.

## Product scope

The maintained workflow is local Docker Compose with ephemeral personal data.
The application and database ports are bound to localhost; do not add
multi-user authorization, durable personal-data storage, or Kubernetes
deployment without a new product requirement.

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

## Phase 4: Upload-triggered processing with Airflow (complete)

The final web workflow accepts multiple data files from a user and starts
processing when each upload is accepted. Create an independent job and Airflow
DAG run per file so a failed file can be retried without rerunning the other
uploads. The confirmed account scope is one person's combined analytics across
their Telegram accounts; preserve account/source provenance for every import.

Airflow owns task scheduling, dependencies, retries, concurrency, orchestration
history, and pipeline-level failure reporting. FastAPI owns upload validation,
job acceptance, and local job status; app endpoints are unauthenticated and
intended only for localhost use. Reusable application services own parsing,
normalization, imports, and domain logic. DAGs orchestrate those services and
must not duplicate business logic.

Airflow is part of the default Docker Compose stack to exercise the local
end-to-end workflow. Document how to start only named application services
when orchestration is not needed. Keep the importer and services usable without
Airflow.

### 16. Define upload and job lifecycle

- Accept per-file uploads and create a job linked to the source account
  identified from the export. Do not trust a client-supplied account identity
  in place of validating the export.
- Define allowed file types and size limits, ephemeral staging, duplicate
  upload behavior, and job status/error contracts.
- Determine whether existing `import_sessions` can represent import progress
  and link to orchestration history. Add schema only for a demonstrated gap;
  avoid duplicating status records.
- Keep uploads and job history within the single local owner scope; do not add
  app users or ownership authorization.

### 17. Make application pipeline services reusable

- Wrap or extract export validation, Telegram parsing/import, identity
  reconciliation, and any necessary post-import operation as callable
  application services.
- Keep the existing CLI using the same services so core processing remains
  independently testable and runnable without a scheduler.
- Preserve explicit transaction boundaries, existing idempotency and source
  provenance. Do not add materialized analytics or recomputation unless
  measured query cost justifies it.

### 18. Dispatch reliably and orchestrate each file

- Stage the uploaded file and persist the job before triggering Airflow. Use stable
  job/run identifiers and define recovery for scheduler/API outages, duplicate
  trigger requests, ambiguous trigger timeouts, and accepted uploads that
  never start.
- Build a per-file DAG for validation, import, any required post-import work,
  and final status reporting. Scope every task to its job and source account.
- Define task dependencies, concurrency limits, timeouts, and retry policies:
  retry transient failures, but fail invalid input without futile retries.
- Pass only safe identifiers and storage references between tasks. Never put
  raw exports or message contents into XCom, task logs, or error summaries.

### 19. Add Airflow to the default local Compose stack

- Add the minimum Airflow API/scheduler/task-processing services, initialization,
  health checks, ephemeral Airflow metadata storage, and RAM-backed shared
  upload staging needed for local execution.
- Keep Airflow metadata separate from application data/schema. Use a simple
  single-host executor for local development; defer distributed workers until
  workload evidence requires them.
- Package the same application services and pinned dependencies into the task
  environment. Do not assume the host virtual environment provides container
  dependencies.
- Make `docker compose up --build` start the complete local workflow and apply
  application migrations automatically. Document upload/job access and the
  separate local Airflow UI account.

### 20. Expose job history and verify failure recovery

- Expose safe per-file status, timestamps, duration, and error summaries, with
  links between upload jobs, import sessions, and Airflow runs.
- Test multiple uploads, success, malformed/missing files, duplicate inputs,
  transient retries, trigger recovery, partial failure and rollback, concurrent
  imports from separate accounts, and correct counts after reruns.
- Verify that logs, API errors, and orchestration metadata contain no private
  export or message data.

### 21. Add scheduled processing only for a defined need

- Uploaded files trigger processing immediately; scheduling is not needed for
  this flow.
- Add a schedule only after defining automatic input discovery, immutability
  or change detection, retention, and incremental processing semantics. Do
  not repeatedly process a mutable personal-export path without these rules.

**Phase 4 exit criteria:** each uploaded file has an independent inspectable
job and DAG run; accepted uploads have a recovery path if dispatch fails;
retries and repeated imports do not duplicate messages; task history and safe
errors are available; the default Compose stack runs the pipeline; and the
CLI/services remain usable without Airflow.

## Phase 5: Expand the data platform

### 22. Select and add another messaging platform

- Selected **Instagram** after comparing official export availability.
  Instagram and Facebook offer Meta-account data exports with a JSON option;
  WhatsApp chat export is text-oriented, and VK's official archive format was
  not established as a stable machine-readable message format. Instagram is
  the selected direct-message source, not a claim that its archive schema or
  message IDs are stable.
- Parse the official Instagram ZIP archive in memory and validate conversation
  JSON. Preserve available platform IDs, raw message payload, and
  source-account/platform provenance. Do not infer participant identity from
  display names; keep direction unknown unless explicitly provided.
- Store a deterministic importer record key for idempotency when a platform
  message ID is absent, without representing that key as an Instagram ID.
- Select Telegram or Instagram in the upload workflow; process Telegram JSON
  and Instagram ZIP exports through the same per-file Airflow pipeline.
- Keep existing analytics scoped to Telegram. Cross-platform identity linking
  and analytics remain deferred to sections 23–24.
- Cover synthetic fixtures, malformed input, repeated imports, migration
  preservation, workflow dispatch, and Telegram behavior with tests.

### 23. Add explicit cross-platform identity links

- Import Instagram address-book contacts from supported JSON entries with
  stable, account-local source keys so re-imports do not duplicate contacts.
  Contacts without a reliable platform user ID remain account-local and
  cannot be identity-linked.
- Add explicit identity groups across platforms, with at most one identity
  per platform in a group. Record link/unlink actions, both involved identity
  IDs, timestamps, and the dashboard as provenance.
- Let the owner explicitly link and unlink identities through the dashboard.
  Reject conflicts with an existing group or another identity on the same
  platform; require unlinking first instead of silently merging groups.
- Never infer cross-platform identity from display names, usernames, or
  contact-book position. Keep cross-platform aggregates deferred to section
  24.
- Cover synthetic address-book imports, idempotency, malformed input,
  migration preservation, conflict handling, unlinking, and provenance.

### 24. Build cross-platform communication analysis

- Add analyses only after identity links and direction semantics are reliable
  and testable.
- Preserve platform, source account, owner/contact direction, and other
  necessary provenance; define which totals are meaningfully comparable.
- Verify that linked identities or conversations do not cause duplicate
  counting.

### 25. Scale imports and derived analytics based on measurements

- Profile representative synthetic large imports and analytics before adding
  streaming/chunked parsing, bulk operations, checkpoints, or precomputed
  results.
- Define refresh/invalidation behavior for imports and identity changes before
  materializing results.
- Preserve transaction safety, import-session counts, uniqueness, safe retries,
  and full re-import semantics for any incremental ingestion.

**Phase 5 exit criteria:** at least one additional importer runs through the
same reusable upload pipeline; cross-platform links are explicit and auditable;
combined analytics preserve provenance; and any incremental processing is
safe to retry and validated against a full re-import.

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

1. Per-file local upload contract, ephemeral staging, and job lifecycle.
2. Reusable retry-safe pipeline services and reliable Airflow dispatch/recovery.
3. Per-file Airflow DAG, default Compose integration, job status/history, and
   operational/privacy tests.
4. Select one additional messaging platform and implement its importer through
   the upload pipeline.
5. Explicit cross-platform identity links and provenance-preserving analytics;
   profile before scaling imports or materializing analytics.
