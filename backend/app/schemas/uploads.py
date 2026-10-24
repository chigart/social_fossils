from datetime import datetime

from pydantic import BaseModel


class UploadJobResponse(BaseModel):
    id: int
    filename: str
    platform: str
    status: str
    source_account_id: int | None
    import_session_id: int | None
    airflow_dag_run_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
