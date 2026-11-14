import hashlib
import json

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import AnalyticsCacheEntry, IdentityLinkEvent, ImportSession

# Increment when response semantics change without a database revision change.
CACHE_VERSION = 1


def analytics_revision(db: Session) -> str:
    row = db.execute(
        select(
            select(func.count(ImportSession.id)).scalar_subquery(),
            select(func.max(ImportSession.id)).scalar_subquery(),
            select(func.max(ImportSession.finished_at)).scalar_subquery(),
            select(func.count(IdentityLinkEvent.id)).scalar_subquery(),
            select(func.max(IdentityLinkEvent.id)).scalar_subquery(),
        )
    ).one()
    return json.dumps([CACHE_VERSION, *row], default=str)


def analytics_cache_key(path: str, query: str) -> str:
    return hashlib.sha256(f"{path}?{query}".encode("utf-8")).hexdigest()


def read_cached_response(db: Session, key: str, revision: str) -> str | None:
    return db.scalar(
        select(AnalyticsCacheEntry.response_body).where(
            AnalyticsCacheEntry.cache_key == key,
            AnalyticsCacheEntry.revision == revision,
        )
    )


def store_cached_response(db: Session, key: str, revision: str, body: str) -> None:
    if analytics_revision(db) != revision:
        return
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        insert = postgres_insert(AnalyticsCacheEntry)
    elif dialect == "sqlite":
        insert = sqlite_insert(AnalyticsCacheEntry)
    else:
        raise RuntimeError(f"Unsupported analytics cache database: {dialect}")
    statement = insert.values(cache_key=key, revision=revision, response_body=body)
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[AnalyticsCacheEntry.cache_key],
            set_={"revision": revision, "response_body": body},
        )
    )
    db.commit()
