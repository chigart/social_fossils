# System architecture

The default local Compose stack separates the browser UI, FastAPI application,
Airflow orchestration, and application database. The upload staging volume is
shared between the API and Airflow tasks. Publicly exposed service ports are
bound to localhost.

```mermaid
flowchart LR
    Browser["Browser"]

    subgraph Compose["Docker Compose"]
        Frontend["frontend<br/>React app served by Nginx<br/>localhost:3000"]
        Backend["backend<br/>FastAPI + SQLAlchemy<br/>Alembic migrations at startup<br/>localhost:8000"]
        AppDB[("db<br/>PostgreSQL application data")]
        Adminer["adminer<br/>localhost:8081"]
        DAG["Import DAG<br/>airflow/dags/import.py"]

        subgraph Airflow["Airflow"]
            API["airflow-api<br/>REST API<br/>localhost:8080"]
            Scheduler["airflow-scheduler<br/>LocalExecutor"]
            Processor["airflow-dag-processor"]
            Init["airflow-init"]
            MetaDB[("airflow-db<br/>metadata")]
            Logs[("airflow_logs<br/>tmpfs")]
            Secrets[("airflow_secrets_shared")]
        end

        Uploads[("uploads<br/>shared tmpfs staging")]
        PGVolume[("postgres_data<br/>persistent volume")]
    end

    Ollama["Optional host Ollama"]

    Browser --> Frontend
    Frontend -->|"/api/* proxy"| Backend
    Backend --> AppDB
    AppDB --- PGVolume
    Adminer --> AppDB
    Backend -->|"trigger / inspect DAG runs"| API
    Backend --- Uploads

    API --> MetaDB
    Scheduler --> MetaDB
    Processor --> MetaDB
    Init --> MetaDB
    Scheduler --> Processor
    Processor --> DAG
    API --- Logs
    Scheduler --- Logs
    Processor --- Logs
    Init --- Secrets
    API --- Secrets
    Scheduler --- Secrets
    Processor --- Secrets
    Scheduler --- Uploads
    Processor --- Uploads
    Scheduler -->|"run import DAG tasks"| AppDB
    Backend -. "optional AI requests" .-> Ollama
```

`uploads` and `airflow_logs` are RAM-backed Compose volumes. `airflow-db` also
uses a temporary filesystem; the application PostgreSQL data uses the
`postgres_data` named volume. The frontend and application API, PostgreSQL,
Airflow API, and Adminer host ports are bound to `127.0.0.1`.

The browser sends API requests through the frontend's Nginx `/api/` proxy.
During imports, FastAPI creates jobs and triggers Airflow; Airflow runs the
import tasks against the shared staged file and the application database.
Parsing and platform-specific persistence remain in backend importer/parser
modules rather than the DAG. Ollama is optional and runs outside Compose when
configured.
