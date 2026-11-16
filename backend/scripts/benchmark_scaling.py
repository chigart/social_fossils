from __future__ import annotations

import argparse
import cProfile
import gc
import json
import os
import platform
import pstats
import tempfile
import tracemalloc
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def _write_telegram_export(path: Path, message_count: int) -> None:
    with path.open("w", encoding="utf-8") as export_file:
        export_file.write(
            '{"personal_information":{"user_id":1000,"first_name":"Synthetic"},'
            '"contacts":{"list":[]},'
            '"chats":{"list":[{"id":1,"type":"personal_chat",'
            '"name":"Synthetic conversation","messages":['
        )
        for index in range(message_count):
            if index:
                export_file.write(",")
            message = {
                "id": index + 1,
                "type": "message",
                "date_unixtime": str(1_609_459_200 + index * 3600),
                "from": "Synthetic owner" if index % 2 == 0 else "Synthetic peer",
                "from_id": "user1000" if index % 2 == 0 else "user2000",
                "text": "synthetic benchmark text alpha beta",
            }
            json.dump(message, export_file, separators=(",", ":"))
        export_file.write("]}]}}")


def _write_instagram_export(path: Path, message_count: int) -> None:
    profile_path = (
        "your_instagram_activity/personal_information/"
        "personal_information.json"
    )
    messages_path = (
        "your_instagram_activity/messages/inbox/"
        "synthetic_peer_2000/message_1.json"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(
            profile_path,
            json.dumps(
                {
                    "profile_user": [
                        {
                            "string_map_data": {
                                "Username": {"value": "synthetic_owner"},
                                "Name": {"value": "Synthetic Owner"},
                                "User ID": {"value": "owner-1000"},
                            }
                        }
                    ]
                },
                separators=(",", ":"),
            ),
        )
        with archive.open(messages_path, "w") as message_file:
            message_file.write(
                b'{"title":"Synthetic conversation",'
                b'"participants":[{"name":"Synthetic owner"},'
                b'{"name":"Synthetic peer"}],"messages":['
            )
            for index in range(message_count):
                if index:
                    message_file.write(b",")
                outgoing = index % 2 == 0
                message = {
                    "sender_name": (
                        "Synthetic owner" if outgoing else "Synthetic peer"
                    ),
                    "sender_id": "owner-1000" if outgoing else "2000",
                    "timestamp_ms": (1_609_459_200 + index * 3600) * 1000,
                    "content": "synthetic benchmark text alpha beta",
                    "is_outgoing": outgoing,
                }
                message_file.write(
                    json.dumps(message, separators=(",", ":")).encode("utf-8")
                )
            message_file.write(b"]}")


def _create_schema(engine: Any) -> None:
    statements = (
        "CREATE TABLE account ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, platform VARCHAR(50), "
        "name VARCHAR(200), username VARCHAR(100), "
        "platform_user_id VARCHAR(100), created_at DATETIME)",
        "CREATE TABLE canonical_identities ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, platform VARCHAR(50), "
        "platform_user_id VARCHAR(100), identity_group_id INTEGER, "
        "created_at DATETIME, UNIQUE(platform, platform_user_id))",
        "CREATE TABLE contacts ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, "
        "platform VARCHAR(50), platform_user_id VARCHAR(100), "
        "source_contact_key VARCHAR(64), canonical_identity_id INTEGER, "
        "display_name VARCHAR(300), username VARCHAR(100), created_at DATETIME, "
        "UNIQUE(account_id, platform_user_id), "
        "UNIQUE(account_id, source_contact_key))",
        "CREATE TABLE chats ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, "
        "platform VARCHAR(50), chat_id VARCHAR(500), chat_type VARCHAR(50), "
        "title VARCHAR(300), created_at DATETIME, "
        "UNIQUE(account_id, chat_id))",
        "CREATE TABLE messages ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, "
        "platform VARCHAR(50), message_id VARCHAR(100), "
        "source_record_key VARCHAR(64), sender_id VARCHAR(100), "
        "sender_contact_id INTEGER, sender_name VARCHAR(300), "
        "is_outgoing BOOLEAN, message_date DATETIME, message_type VARCHAR(50), "
        "text_content TEXT, reply_to_telegram_message_id VARCHAR(100), "
        "source_reply_id VARCHAR(200), raw_payload JSON, created_at DATETIME, "
        "UNIQUE(chat_id, message_id), UNIQUE(chat_id, source_record_key))",
        "CREATE INDEX ix_messages_chat_date ON messages(chat_id, message_date)",
        "CREATE INDEX ix_messages_sender ON messages(sender_contact_id)",
        "CREATE TABLE import_sessions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, "
        "platform VARCHAR(50), source_filename VARCHAR(500), "
        "file_sha256 VARCHAR(64), status VARCHAR(20), started_at DATETIME, "
        "finished_at DATETIME, total_messages INTEGER, inserted_messages INTEGER, "
        "updated_messages INTEGER, skipped_messages INTEGER, error_message TEXT, "
        "created_at DATETIME)",
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _measure(
    name: str,
    message_count: int,
    operation: Callable[[], Any],
    *,
    profile: bool,
) -> dict[str, Any]:
    gc.collect()
    profiler = cProfile.Profile() if profile else None
    tracemalloc.start()
    started = perf_counter()
    try:
        if profiler is not None:
            profiler.enable()
        result = operation()
        if profiler is not None:
            profiler.disable()
        elapsed = perf_counter() - started
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    measurement: dict[str, Any] = {
        "name": name,
        "message_count": message_count,
        "elapsed_seconds": round(elapsed, 6),
        "messages_per_second": round(message_count / elapsed, 2)
        if elapsed
        else None,
        "peak_traced_mib": round(peak_bytes / (1024 * 1024), 3),
    }
    if isinstance(result, dict):
        for key in ("total_messages", "inserted_messages", "skipped_messages"):
            if key in result:
                measurement[key] = result[key]
    del result

    if profiler is not None:
        print(f"\nTop profile entries for {name}:")
        pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(12)
    return measurement


def _parse_telegram(path: Path) -> Any:
    from app.parsers.telegram_parser import parse_telegram_export

    with path.open(encoding="utf-8") as export_file:
        return parse_telegram_export(json.load(export_file))


def _parse_instagram(path: Path) -> Any:
    from app.parsers.instagram_parser import parse_instagram_archive

    return parse_instagram_archive(path)


def _run_workload(message_count: int, root: Path, *, profile: bool) -> list[dict[str, Any]]:
    from app.importers.instagram_importer import import_instagram_export
    from app.routers.analytics_chat_insights import get_chat_insights
    from app.routers.analytics_communication_balance import (
        get_communication_balance,
    )
    from app.routers.analytics_communication_timeline_queries import (
        build_communication_timeline_statistics,
    )
    from app.routers.analytics_forgotten_contacts import (
        build_forgotten_contacts_statistics,
    )
    from app.routers.analytics_overview import get_chat_statistics, get_overview
    from app.routers.analytics_contacts import get_contact_statistics
    from app.importers.telegram_importer import import_telegram_export

    telegram_path = root / "synthetic-telegram.json"
    instagram_path = root / "synthetic-instagram.zip"
    _write_telegram_export(telegram_path, message_count)
    _write_instagram_export(instagram_path, message_count)

    measurements = [
        _measure(
            "telegram_parse",
            message_count,
            lambda: _parse_telegram(telegram_path),
            profile=profile,
        ),
        _measure(
            "instagram_parse",
            message_count,
            lambda: _parse_instagram(instagram_path),
            profile=profile,
        ),
    ]

    database_path = root / "synthetic.sqlite"
    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    _create_schema(engine)
    try:
        with Session(engine) as session:
            measurements.append(
                _measure(
                    "telegram_import_fresh",
                    message_count,
                    lambda: import_telegram_export(telegram_path, session=session),
                    profile=profile,
                )
            )
            measurements.append(
                _measure(
                    "instagram_import_fresh",
                    message_count,
                    lambda: import_instagram_export(instagram_path, session=session),
                    profile=profile,
                )
            )
            measurements.append(
                _measure(
                    "telegram_import_repeat",
                    message_count,
                    lambda: import_telegram_export(telegram_path, session=session),
                    profile=profile,
                )
            )
            measurements.append(
                _measure(
                    "instagram_import_repeat",
                    message_count,
                    lambda: import_instagram_export(instagram_path, session=session),
                    profile=profile,
                )
            )

            analytics = (
                ("analytics_overview", lambda: get_overview(session)),
                ("analytics_chats", lambda: get_chat_statistics(session)),
                ("analytics_contacts", lambda: get_contact_statistics(session)),
                ("analytics_chat_insights", lambda: get_chat_insights(session)),
                (
                    "analytics_communication_balance",
                    lambda: get_communication_balance(session),
                ),
                (
                    "analytics_communication_timeline",
                    lambda: build_communication_timeline_statistics(session),
                ),
                (
                    "analytics_forgotten_contacts",
                    lambda: build_forgotten_contacts_statistics(
                        session,
                        as_of=datetime(2030, 1, 1, tzinfo=timezone.utc),
                    ),
                ),
            )
            for name, operation in analytics:
                measurements.append(
                    _measure(
                        name,
                        message_count * 2,
                        operation,
                        profile=profile,
                    )
                )
    finally:
        engine.dispose()
    return measurements


def _positive_counts(value: str) -> list[int]:
    try:
        counts = [int(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "message counts must be comma-separated positive integers"
        ) from exc
    if not counts or any(count <= 0 for count in counts):
        raise argparse.ArgumentTypeError(
            "message counts must be comma-separated positive integers"
        )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Measure synthetic Telegram/Instagram imports and derived analytics "
            "using an isolated SQLite database."
        )
    )
    parser.add_argument(
        "--messages",
        type=_positive_counts,
        default=[1000, 5000],
        help="comma-separated messages per platform (default: 1000,5000)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="print cumulative cProfile entries for each measured operation",
    )
    args = parser.parse_args()

    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    results: dict[str, Any] = {
        "python": platform.python_version(),
        "database": "isolated SQLite; timings are not PostgreSQL latency estimates",
        "timings_include_tracemalloc": True,
        "profile_enabled": args.profile,
        "workloads": [],
    }
    with tempfile.TemporaryDirectory(prefix="social-fossils-benchmark-") as temp_dir:
        root = Path(temp_dir)
        for message_count in args.messages:
            sample_dir = root / str(message_count)
            sample_dir.mkdir()
            results["workloads"].append(
                {
                    "messages_per_platform": message_count,
                    "measurements": _run_workload(
                        message_count,
                        sample_dir,
                        profile=args.profile,
                    ),
                }
            )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
