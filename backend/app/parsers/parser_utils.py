from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any


def source_id(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    normalized = str(value).strip()
    return normalized or None


def timestamp_from_message(message: dict[str, Any]) -> datetime | None:
    value = message.get("timestamp_ms")
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, float) and (
        not math.isfinite(value) or not value.is_integer()
    ):
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (OverflowError, OSError, TypeError, ValueError):
        return None


def stable_record_key(
    chat_id: str,
    raw_message: dict[str, Any],
    occurrence: int,
) -> str:
    serialized = json.dumps(
        [chat_id, raw_message, occurrence],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def chat_type(participants: Any) -> str:
    if not isinstance(participants, list):
        return "unknown"
    identities: set[tuple[str, str] | tuple[str, int]] = set()
    for index, participant in enumerate(participants):
        if isinstance(participant, dict):
            user_id = source_id(
                participant.get(
                    "user_id",
                    participant.get("id", participant.get("participant_id")),
                )
            )
            if user_id is not None:
                identities.add(("id", user_id))
                continue
            name = participant.get("name")
            if isinstance(name, dict):
                name = name.get("value", name.get("full_name"))
            if isinstance(name, str) and name.strip():
                identities.add(("name", name.strip().casefold()))
                continue
        identities.add(("unknown", index))
    if len(identities) < 2:
        return "unknown"
    return "private_group" if len(identities) > 2 else "personal_chat"
