# Upload and import logic

## Upload acceptance and dispatch

```mermaid
flowchart TD
    Start["Receive file and platform"]
    Platform{"Known platform?"}
    Extension{"Filename extension allowed<br/>for that platform?"}
    Read["Read upload bytes"]
    Size{"Non-empty and under<br/>configured maximum size?"}
    Hash["Compute SHA-256"]
    Write["Write bytes to staging<br/>using digest as path"]
    Duplicate{"Digest seen in an<br/>earlier UploadJob?"}
    Create["Create new UploadJob<br/>status: pending"]
    Trigger{"Airflow trigger returns<br/>a DAG run ID?"}
    Linked["Save DAG run ID<br/>clear dispatch error"]
    FailedDispatch["Keep pending job;<br/>save dispatch error"]
    Response["Return accepted job<br/>and duplicate warning if applicable"]
    Reject["Return validation error"]

    Start --> Platform
    Platform -->|"No"| Reject
    Platform -->|"Yes"| Extension
    Extension -->|"No"| Reject
    Extension -->|"Yes"| Read --> Size
    Size -->|"No"| Reject
    Size -->|"Yes"| Hash --> Write --> Duplicate --> Create --> Trigger
    Trigger -->|"Yes"| Linked --> Response
    Trigger -->|"No"| FailedDispatch --> Response
    Duplicate -->|"Yes: warn, do not block"| Create
```

A repeated digest does not reuse an old job or stop a new import. This permits
re-imports while message-level uniqueness makes persistence idempotent. A
dispatch failure leaves a pending job without an Airflow run ID; only such
pending jobs can be retried through the retry endpoint.

## Airflow tasks and import persistence

```mermaid
flowchart TD
    Run["DAG run receives job_id"]
    Job{"UploadJob exists?"}
    File{"Staged path exists<br/>and is a regular file?"}
    Start["Set job to processing<br/>record started_at"]
    Dispatch["Route platform to importer"]
    Parse["Parser validates and<br/>normalizes platform export"]
    Save["Insert/update supported entities<br/>and deduplicate messages"]
    Session["Record ImportSession counts,<br/>status, and timestamps"]
    Complete["Set job completed<br/>record finished_at and run ID"]
    Retry["Airflow retries failed task<br/>(2 retries, 5-minute delay)"]
    Failed["Failure task records failed status,<br/>finished_at, run ID, and error"]
    Stop["Import stops with error"]

    Run --> Job
    Job -->|"No"| Stop
    Job -->|"Yes"| File
    File -->|"No"| Stop
    File -->|"Yes"| Start --> Dispatch --> Parse --> Save --> Session --> Complete
    Dispatch -->|"Unsupported platform,<br/>parse or database failure"| Retry
    Parse -->|"Invalid export"| Retry
    Save -->|"Persistence failure"| Retry
    Retry -->|"Retry succeeds"| Save
    Retry -->|"Retries exhausted or task fails"| Failed
    Run -. "validation failure" .-> Failed
    Complete -. "completion task failure" .-> Failed
```

The DAG order is `validate_export -> perform_import -> mark_completed`.
`mark_failed` is a `ONE_FAILED` task downstream of the validation, import, and
completion tasks. Airflow may retry failed work before the failure task records
the terminal job status.

Each platform importer uses its parser and SQLAlchemy models. It records
`ImportSession` status, timestamps, and message counts; failures roll back the
import transaction and propagate to Airflow. Re-imports use database uniqueness
and `ON CONFLICT DO NOTHING` for messages rather than overwriting existing
messages.
