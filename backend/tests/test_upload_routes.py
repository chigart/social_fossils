from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy import Table, create_engine
from sqlalchemy.orm import Session

from app.db import Base, get_db
from app.main import app
from app.models import UploadJob
from app.routers import upload


class FakeAirflowClient:
    def trigger_dag_run(self, _dag_id, _conf, **_kwargs):
        return {"dag_run_id": "run-1"}

    def get_dag_run(self, _dag_id, _run_id):
        return {"state": "success", "start_date": None, "end_date": None}

    def get_dag_run_tasks(self, _dag_id, _run_id):
        return []


def test_upload_and_job_routes_are_local_and_unauthenticated(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'uploads.db'}",
        connect_args={"check_same_thread": False},
    )
    cast(Table, UploadJob.__table__).create(engine)
    session = Session(engine)
    monkeypatch.setattr(upload.settings, "upload_staging_dir", str(tmp_path / "staging"))
    monkeypatch.setattr(upload, "get_airflow_client", FakeAirflowClient)

    def override_get_db():
        yield session

    with TestClient(app) as client:
        app.dependency_overrides[get_db] = override_get_db
        try:
            uploaded = client.post(
                "/api/uploads/upload",
                data={"platform": "telegram"},
                files={"file": ("export.json", b'{"synthetic": true}', "application/json")},
            )
            assert uploaded.status_code == 202
            job = uploaded.json()
            assert job["status"] == "pending"
            assert job["airflow_dag_run_id"] == "run-1"
            assert job["error_message"] is None

            jobs = client.get("/api/uploads/jobs")
            assert jobs.status_code == 200
            assert [item["id"] for item in jobs.json()] == [job["id"]]

            status = client.get(f"/api/uploads/jobs/{job['id']}/status")
            assert status.status_code == 200
            assert status.json()["airflow_run_details"]["state"] == "success"

            duplicate = client.post(
                "/api/uploads/upload",
                data={"platform": "telegram"},
                files={"file": ("another-name.json", b'{"synthetic": true}', "application/json")},
            )
            assert duplicate.status_code == 202
            assert duplicate.json()["warning_message"] == (
                "This file has already been uploaded"
            )
            assert duplicate.json()["airflow_dag_run_id"] == "run-1"
            assert len(client.get("/api/uploads/jobs").json()) == 2
            assert len(list((tmp_path / "staging").iterdir())) == 1

            assert client.post("/api/auth/login", json={}).status_code == 404
            missing_platform = client.post(
                "/api/uploads/upload",
                files={"file": ("export.json", b'{"another": true}', "application/json")},
            )
            assert missing_platform.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)
            session.close()
            engine.dispose()


def test_upload_job_schema_has_no_app_user():
    assert "users" not in Base.metadata.tables
    assert "user_id" not in UploadJob.__table__.columns
    assert UploadJob.__table__.c.platform.default is None
    assert UploadJob.__table__.c.platform.server_default is None


def test_zip_platform_uploads_record_platform_and_require_zip_archive(
    tmp_path,
    monkeypatch,
):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'instagram-uploads.db'}",
        connect_args={"check_same_thread": False},
    )
    cast(Table, UploadJob.__table__).create(engine)
    session = Session(engine)
    monkeypatch.setattr(
        upload.settings,
        "upload_staging_dir",
        str(tmp_path / "staging"),
    )
    monkeypatch.setattr(upload, "get_airflow_client", FakeAirflowClient)

    def override_get_db():
        yield session

    with TestClient(app) as client:
        app.dependency_overrides[get_db] = override_get_db
        try:
            response = client.post(
                "/api/uploads/upload",
                data={"platform": "instagram"},
                files={
                    "file": (
                        "instagram.zip",
                        b"synthetic archive",
                        "application/zip",
                    )
                },
            )
            assert response.status_code == 202
            assert response.json()["platform"] == "instagram"

            invalid = client.post(
                "/api/uploads/upload",
                data={"platform": "instagram"},
                files={
                    "file": (
                        "instagram.json",
                        b"synthetic export",
                        "application/json",
                    )
                },
            )
            assert invalid.status_code == 400
            assert ".zip" in invalid.json()["detail"]

            facebook = client.post(
                "/api/uploads/upload",
                data={"platform": "facebook"},
                files={
                    "file": (
                        "facebook.zip",
                        b"synthetic archive",
                        "application/zip",
                    )
                },
            )
            assert facebook.status_code == 202
            assert facebook.json()["platform"] == "facebook"

            invalid_facebook = client.post(
                "/api/uploads/upload",
                data={"platform": "facebook"},
                files={
                    "file": (
                        "facebook.html",
                        b"synthetic export",
                        "text/html",
                    )
                },
            )
            assert invalid_facebook.status_code == 400
            assert ".zip" in invalid_facebook.json()["detail"]

            vk = client.post(
                "/api/uploads/upload",
                data={"platform": "vk"},
                files={
                    "file": (
                        "vk.zip",
                        b"synthetic archive",
                        "application/zip",
                    )
                },
            )
            assert vk.status_code == 202
            assert vk.json()["platform"] == "vk"

            invalid_vk = client.post(
                "/api/uploads/upload",
                data={"platform": "vk"},
                files={
                    "file": (
                        "vk.html",
                        b"synthetic export",
                        "text/html",
                    )
                },
            )
            assert invalid_vk.status_code == 400
            assert ".zip" in invalid_vk.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_db, None)
            session.close()
            engine.dispose()


def test_pending_upload_without_airflow_run_can_be_retried(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'retry.db'}",
        connect_args={"check_same_thread": False},
    )
    cast(Table, UploadJob.__table__).create(engine)
    session = Session(engine)
    monkeypatch.setattr(upload, "get_airflow_client", FakeAirflowClient)
    job = UploadJob(
        filename="export.json",
        platform="telegram",
        file_sha256="a" * 64,
        file_size=1,
        status="pending",
        error_message="Pipeline dispatch failed",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    def override_get_db():
        yield session

    with TestClient(app) as client:
        app.dependency_overrides[get_db] = override_get_db
        try:
            response = client.post(f"/api/uploads/jobs/{job.id}/retry")

            assert response.status_code == 200
            assert response.json()["airflow_dag_run_id"] == "run-1"
            assert response.json()["error_message"] is None

            repeated = client.post(f"/api/uploads/jobs/{job.id}/retry")
            assert repeated.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)
            session.close()
            engine.dispose()
