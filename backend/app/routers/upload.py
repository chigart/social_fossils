import hashlib
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.airflow_client import get_airflow_client
from app.config import settings
from app.db import get_db
from app.models import UploadJob
from app.schemas.uploads import UploadJobResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


def _ensure_upload_dir() -> Path:
    upload_dir = Path(settings.upload_staging_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def dispatch_job_to_airflow(job_id: int, session: Session) -> str:
    try:
        job = session.query(UploadJob).filter(UploadJob.id == job_id).first()
        if not job:
            raise ValueError(f"Upload job {job_id} was not found")

        client = get_airflow_client()
        result = client.trigger_dag_run(
            settings.airflow_dag_id,
            {"job_id": job_id},
            dag_run_id=f"upload_job_{job_id}",
            logical_date=job.created_at,
        )
        dag_run_id = result.get("dag_run_id")
        if not dag_run_id:
            raise RuntimeError("Airflow accepted the trigger without returning a run ID")

        job.airflow_dag_run_id = dag_run_id
        job.error_message = None
        session.commit()

        logger.info(f"Triggered Airflow DAG run {dag_run_id} for job {job_id}")
        return dag_run_id
    except Exception as e:
        logger.error(f"Failed to trigger Airflow DAG for job {job_id}: {e}")
        raise


async def _save_uploaded_file(file: UploadFile) -> tuple[str, int]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    # Check file size
    contents = await file.read()
    file_size = len(contents)
    if file_size > settings.upload_max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.upload_max_size_bytes} bytes",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file not allowed",
        )

    # Calculate SHA256
    sha256_hash = hashlib.sha256(contents).hexdigest()

    # Save to staging directory
    upload_dir = _ensure_upload_dir()
    file_path = upload_dir / sha256_hash
    with open(file_path, "wb") as f:
        f.write(contents)

    return sha256_hash, file_size


@router.post("/upload", response_model=UploadJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(...),
    source_account_id: int | None = Form(None),
    session: Session = Depends(get_db),
):
    try:
        file_sha256, file_size = await _save_uploaded_file(file)

        # Check for duplicate upload
        existing_job = (
            session.query(UploadJob)
            .filter(UploadJob.file_sha256 == file_sha256)
            .first()
        )

        if existing_job:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This file has already been uploaded",
            )

        # Create upload job
        job = UploadJob(
            filename=file.filename or "unknown",
            file_sha256=file_sha256,
            file_size=file_size,
            status="pending",
            source_account_id=source_account_id,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        # Dispatch to Airflow
        try:
            dispatch_job_to_airflow(job.id, session)
            logger.info(f"Job {job.id} dispatched to Airflow")
        except Exception as e:
            logger.error(f"Failed to dispatch job {job.id} to Airflow: {e}")
            job.error_message = f"Pipeline dispatch failed: {e}"
            session.commit()

        return UploadJobResponse.model_validate(job)

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )


@router.get("/jobs/{job_id}/status")
def get_job_status(
    job_id: int,
    session: Session = Depends(get_db),
):
    """Get detailed job status including Airflow run information."""
    job = session.query(UploadJob).filter(UploadJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    response = UploadJobResponse.model_validate(job).model_dump()

    # Get Airflow run details if available
    if job.airflow_dag_run_id:
        try:
            client = get_airflow_client()
            run_details = client.get_dag_run(
                settings.airflow_dag_id,
                job.airflow_dag_run_id,
            )
            response["airflow_run_details"] = {
                "state": run_details.get("state"),
                "start_date": run_details.get("start_date"),
                "end_date": run_details.get("end_date"),
            }

            # Get task details
            task_instances = client.get_dag_run_tasks(
                settings.airflow_dag_id,
                job.airflow_dag_run_id,
            )
            response["airflow_tasks"] = [
                {
                    "task_id": t.get("task_id"),
                    "state": t.get("state"),
                    "start_date": t.get("start_date"),
                    "end_date": t.get("end_date"),
                }
                for t in task_instances
            ]
        except Exception as e:
            logger.error(f"Failed to fetch Airflow details for job {job_id}: {e}")
            response["airflow_error"] = str(e)

    return response


@router.post("/jobs/{job_id}/retry", response_model=UploadJobResponse)
def retry_job_dispatch(
    job_id: int,
    session: Session = Depends(get_db),
):
    job = session.query(UploadJob).filter(UploadJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status != "pending" or job.airflow_dag_run_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending jobs without an Airflow run can be retried",
        )

    try:
        dispatch_job_to_airflow(job.id, session)
    except Exception as e:
        session.rollback()
        job = session.query(UploadJob).filter(UploadJob.id == job_id).first()
        if job:
            job.error_message = f"Pipeline dispatch failed: {e}"
            session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to start the pipeline for job {job_id}: {e}",
        ) from e

    session.refresh(job)
    return UploadJobResponse.model_validate(job)


@router.get("/jobs", response_model=list[UploadJobResponse])
def list_jobs(
    session: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    jobs = (
        session.query(UploadJob)
        .order_by(UploadJob.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [UploadJobResponse.model_validate(job) for job in jobs]
