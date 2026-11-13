from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Message


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        while chunk := source_file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def insert_message_batch(
    session: Session,
    values: list[dict[str, Any]],
    *,
    conflict_columns: list[str] | None = None,
) -> int:
    statement = insert(Message).values(values)
    if conflict_columns is None:
        statement = statement.on_conflict_do_nothing()
    else:
        statement = statement.on_conflict_do_nothing(
            index_elements=conflict_columns
        )
    statement = statement.returning(Message.id)
    return len(session.execute(statement).scalars().all())
