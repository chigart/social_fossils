# Data flow

## Upload, import, and dashboard

```mermaid
flowchart TD
    User["User selects export and platform"]
    UI["Upload UI and queue"]
    API["FastAPI upload endpoint"]
    Validate{"Platform and filename<br/>extension supported?"}
    Bytes{"Non-empty and within<br/>configured size limit?"}
    Stage["Hash file with SHA-256<br/>write to shared staging volume"]
    Job["Create UploadJob<br/>status: pending"]
    Trigger["Trigger Airflow import DAG<br/>with job ID"]
    DAG["Validate staged job/file"]
    Route["Select platform importer"]
    Parse["Platform parser<br/>normalizes export data"]
    Persist["Importer writes accounts,<br/>chats, contacts, messages,<br/>and ImportSession"]
    DB[("Application PostgreSQL")]
    Fail["Record failed job or<br/>dispatch error"]
    Analytics["Analytics / identity-link APIs"]
    Cache["Read or update analytics<br/>response cache"]
    Hooks["Dashboard hooks and API client"]
    View["Dashboard views"]

    User --> UI --> API --> Validate
    Validate -->|"No"| Fail
    Validate -->|"Yes"| Bytes
    Bytes -->|"No"| Fail
    Bytes -->|"Yes"| Stage --> Job --> Trigger --> DAG
    Trigger -->|"Dispatch unavailable"| Fail
    DAG -->|"Valid"| Route --> Parse --> Persist --> DB
    DAG -->|"Invalid or missing file"| Fail
    Persist -->|"job completed / ImportSession"| DB
    DB --> Analytics --> Cache
    Cache --> Hooks --> View
    DB -. "new imports or identity events change cache revision" .-> Cache
```

Supported exports are Telegram JSON, Instagram/Facebook ZIP archives, and VK
ZIP archives with HTML files. The API stages bytes under their SHA-256 digest;
the filename remains job metadata. Airflow and the backend share the staging
volume, and Airflow calls the backend's platform importer rather than
implementing parsing itself.

Uploading the same file again is allowed. The API reports a duplicate-file
warning, while importer uniqueness constraints and PostgreSQL conflict handling
prevent existing messages from being inserted again.

## Analytics request path

```mermaid
sequenceDiagram
    participant UI as React dashboard
    participant API as FastAPI
    participant Cache as Analytics cache middleware
    participant DB as PostgreSQL

    UI->>API: GET analytics or identity-links
    API->>Cache: Build key from path and query
    Cache->>DB: Read current analytics revision and matching response
    alt Matching cached response exists
        DB-->>Cache: Cached JSON body
        Cache-->>UI: JSON response
    else Cache miss
        Cache->>API: Continue to route
        API->>DB: Run analytics or identity-link query
        DB-->>API: Result rows
        API-->>Cache: HTTP 200 response
        Cache->>DB: Store response if revision has not changed
        Cache-->>UI: JSON response
    end
```

Only GET requests under `/api/analytics/` and `GET /api/identity-links` are
cached. Upload status and other live job information bypass this cache. See
[analytics logic](./analytics.md) for revision and invalidation behavior.
