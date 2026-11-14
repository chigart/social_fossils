from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app import analytics_cache_middleware as middleware
from app.analytics_cache import analytics_cache_key, analytics_revision, store_cached_response


def test_persistent_cache_for_dashboard_and_live_uploads(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'cache.db'}",
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE import_sessions (id INTEGER PRIMARY KEY, finished_at DATETIME)"
        ))
        connection.execute(text(
            "CREATE TABLE identity_link_events (id INTEGER PRIMARY KEY)"
        ))
        connection.execute(text(
            "CREATE TABLE analytics_cache (cache_key VARCHAR(64) PRIMARY KEY, "
            "revision TEXT NOT NULL, response_body TEXT NOT NULL)"
        ))
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(middleware, "SessionLocal", sessions)
    app = FastAPI()
    app.add_middleware(middleware.AnalyticsCacheMiddleware)
    calls: dict[str, int] = {}

    @app.get("/api/analytics/{view}")
    def analytics(view: str, page: int = 1):
        calls[view] = calls.get(view, 0) + 1
        if view == "error":
            return Response(status_code=503)
        return {"view": view, "page": page, "calls": calls[view]}

    @app.get("/api/analytics/group-interactions/{contact_id}")
    def participant(contact_id: int):
        calls["participant"] = calls.get("participant", 0) + 1
        return {"contact_id": contact_id, "calls": calls["participant"]}

    @app.get("/api/analytics/slow/concurrent")
    async def concurrent():
        calls["concurrent"] = calls.get("concurrent", 0) + 1
        await asyncio.sleep(0.1)
        return {"calls": calls["concurrent"]}

    @app.get("/api/identity-links")
    def identity_links():
        calls["identity"] = calls.get("identity", 0) + 1
        return {"calls": calls["identity"]}

    @app.get("/api/uploads/jobs/{job_id}/status")
    def upload_status(job_id: int):
        calls["uploads"] = calls.get("uploads", 0) + 1
        return {"job_id": job_id, "calls": calls["uploads"]}

    @app.post("/api/identity-links")
    def mutate_identity():
        return {"status": "linked"}

    paths = [
        "/api/analytics/overview",
        "/api/analytics/chats?page=1",
        "/api/analytics/contacts",
        "/api/analytics/chat-insights",
        "/api/analytics/communication-balance",
        "/api/analytics/communication-timeline",
        "/api/analytics/forgotten-contacts?scope=private",
        "/api/analytics/forgotten-contacts?scope=group",
        "/api/analytics/group-interactions/42",
        "/api/identity-links",
    ]
    # Simulate another backend process by creating a new client and middleware.
    # The cache is in the database, not in either client's memory.
    with TestClient(app) as client:
        for path in paths:
            response = client.get(path)
            assert response.status_code == 200
            assert client.get(path).json() == response.json()
        assert client.get("/api/analytics/chats?page=2").json()["page"] == 2
        assert client.get("/api/analytics/error").status_code == 503
        assert client.get("/api/analytics/error").status_code == 503
        assert calls["error"] == 2
        with ThreadPoolExecutor(max_workers=2) as executor:
            requests = [
                executor.submit(client.get, "/api/analytics/slow/concurrent")
                for _ in range(2)
            ]
            assert [request.result().json() for request in requests] == [
                {"calls": 1}, {"calls": 1}
            ]
        assert calls["concurrent"] == 1
        assert client.get("/api/uploads/jobs/1/status").json()["calls"] == 1
        assert client.get("/api/uploads/jobs/1/status").json()["calls"] == 2
        assert client.post("/api/identity-links").status_code == 200

    before = dict(calls)
    with TestClient(app) as client:
        for path in paths:
            assert client.get(path).status_code == 200
        assert calls == before
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO import_sessions (id) VALUES (1)"))
        client.get("/api/analytics/overview")
        assert calls["overview"] == before["overview"] + 1
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO identity_link_events (id) VALUES (1)"))
        client.get("/api/identity-links")
        assert calls["identity"] == before["identity"] + 1
        client.get("/api/analytics/overview")
        assert calls["overview"] == before["overview"] + 2


def test_data_change_during_calculation_is_not_cached(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'race.db'}")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE import_sessions (id INTEGER PRIMARY KEY, finished_at DATETIME)"
        ))
        connection.execute(text(
            "CREATE TABLE identity_link_events (id INTEGER PRIMARY KEY)"
        ))
        connection.execute(text(
            "CREATE TABLE analytics_cache (cache_key VARCHAR(64) PRIMARY KEY, "
            "revision TEXT NOT NULL, response_body TEXT NOT NULL)"
        ))
    with sessionmaker(bind=engine)() as session:
        revision = analytics_revision(session)
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO import_sessions (id) VALUES (1)"))
        key = analytics_cache_key("/api/analytics/overview", "")
        store_cached_response(session, key, revision, "{}")
        assert session.scalar(text("SELECT count(*) FROM analytics_cache")) == 0
import asyncio
from concurrent.futures import ThreadPoolExecutor
