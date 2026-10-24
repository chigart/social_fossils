import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import DAG
from airflow.task.trigger_rule import TriggerRule

import sys
sys.path.insert(0, "/app")
from app.db import SessionLocal
from app.telegram_importer import import_source_export
from app.models import UploadJob, ImportSession

logger = logging.getLogger(__name__)

default_args = {
    "owner": "social-fossils",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "import",
    default_args=default_args,
    description="Import a supported messaging-platform export",
    schedule=None,  # Triggered manually
    catchup=False,
    start_date=datetime(2024, 1, 1),
    tags=["import"],
)


def validate_export_file(**context) -> str:
    job_id = context["dag_run"].conf.get("job_id")
    if not job_id:
        raise ValueError("job_id must be provided in DAG run config")

    session = SessionLocal()
    try:
        job = session.query(UploadJob).filter(UploadJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        file_path = Path(f"{os.environ.get('UPLOAD_STAGING_DIR', '/tmp/uploads')}/{job.file_sha256}")
        if not file_path.exists():
            raise FileNotFoundError(f"Upload file not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Upload path is not a file: {file_path}")

        logger.info(f"Upload file validated: {file_path} ({job.file_size} bytes)")
        return str(file_path)
    finally:
        session.close()


def perform_import(**context) -> dict:
    job_id = context["dag_run"].conf.get("job_id")
    
    session = SessionLocal()
    try:
        job = session.query(UploadJob).filter(UploadJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Get the file path from the previous task
        file_path = context["task_instance"].xcom_pull(task_ids="validate_export")

        logger.info(f"Starting import for job {job_id} from {file_path}")

        # Update job status
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        session.commit()

        # Perform the import
        result = import_source_export(job.platform, file_path, session=session)

        # Link the import session to the upload job
        if result.get("session_id"):
            import_session = session.query(ImportSession).filter(
                ImportSession.id == result["session_id"]
            ).first()
            if import_session:
                job.import_session_id = import_session.id
                job.source_account_id = import_session.account_id

        logger.info(f"Import completed for job {job_id}: {result}")
        return result
    finally:
        session.close()


def update_job_status_completed(**context) -> None:
    job_id = context["dag_run"].conf.get("job_id")
    
    session = SessionLocal()
    try:
        job = session.query(UploadJob).filter(UploadJob.id == job_id).first()
        if job:
            job.status = "completed"
            job.finished_at = datetime.now(timezone.utc)
            job.airflow_dag_run_id = context["dag_run"].run_id
            session.commit()
            logger.info(f"Job {job_id} marked as completed")
    finally:
        session.close()


def update_job_status_failed(**context) -> None:
    job_id = context["dag_run"].conf.get("job_id")
    exception = context.get("exception")
    
    session = SessionLocal()
    try:
        job = session.query(UploadJob).filter(UploadJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            job.airflow_dag_run_id = context["dag_run"].run_id
            job.error_message = str(exception) if exception else "Unknown error"
            session.commit()
            logger.error(f"Job {job_id} marked as failed: {job.error_message}")
    finally:
        session.close()


# Define tasks
validate_task = PythonOperator(
    task_id="validate_export",
    python_callable=validate_export_file,
    dag=dag,
)

import_task = PythonOperator(
    task_id="perform_import",
    python_callable=perform_import,
    dag=dag,
)

complete_task = PythonOperator(
    task_id="mark_completed",
    python_callable=update_job_status_completed,
    dag=dag,
)

failure_task = PythonOperator(
    task_id="mark_failed",
    python_callable=update_job_status_failed,
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

# Set dependencies
validate_task >> import_task >> complete_task
[validate_task, import_task, complete_task] >> failure_task
