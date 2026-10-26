from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql

from analytics_test_helpers import add_account, add_chat, add_contact, add_message
from app.models import CanonicalIdentity, Message
from app.routers.analytics_communication_timeline import (
    get_communication_timeline,
)
from app.routers.analytics_communication_timeline_queries import (
    _utc_date_expression,
    _utc_month_expression,
)
from app.schemas.analytics import CommunicationTimelineStatistics
from app.main import app


def test_owner_timeline_uses_utc_months_fills_gaps_and_reports_uncertainty(
    db_session,
):
    add_account(db_session, 1, "user-owner-one", username="owner")
    add_account(db_session, 2, "user-owner-two", username="owner_old")
    add_chat(db_session, 10, 1, "chat-10", chat_type="personal_chat")
    add_chat(db_session, 20, 2, "chat-20", chat_type="personal_chat")
    add_chat(db_session, 30, 1, "group-30", chat_type="supergroup")
    add_contact(db_session, 40, 1, "user-peer", "Peer")

    add_message(
        db_session,
        1,
        10,
        "message",
        "user-owner-one",
        datetime(2024, 12, 31, 23, 0, tzinfo=timezone.utc),
        is_outgoing=True,
    )
    db_session.execute(
        text(
            "UPDATE messages SET message_date = "
            "'2024-12-31 23:30:00-02:00' WHERE id = 1"
        )
    )
    add_message(
        db_session,
        2,
        10,
        "message",
        "user-peer",
        datetime(2025, 1, 2, 12, tzinfo=timezone.utc),
        is_outgoing=False,
    )
    add_message(
        db_session,
        3,
        20,
        "message",
        "user-owner-one",
        datetime(2025, 3, 1, 9, tzinfo=timezone.utc),
        is_outgoing=False,
    )
    add_message(
        db_session,
        4,
        20,
        "message",
        "user-unresolved",
        datetime(2025, 3, 2, 9, tzinfo=timezone.utc),
        is_outgoing=None,
    )
    add_message(
        db_session,
        5,
        30,
        "message",
        None,
        datetime(2025, 3, 3, 9, tzinfo=timezone.utc),
        is_outgoing=None,
    )
    add_message(
        db_session,
        6,
        10,
        "message",
        None,
        message_date=None,
        is_outgoing=None,
    )
    add_message(
        db_session,
        7,
        10,
        "service",
        "user-owner-one",
        datetime(2025, 2, 15, 12, tzinfo=timezone.utc),
        is_outgoing=True,
    )

    result = CommunicationTimelineStatistics.model_validate(
        get_communication_timeline(db_session, None)
    )

    assert result.summary.scope == "owner"
    assert result.summary.canonical_identity_id is None
    assert result.summary.source_account_ids == [1, 2]
    assert result.summary.source_account_labels == ["@owner", "@owner_old"]
    assert result.summary.ordinary_message_count == 6
    assert result.summary.dated_ordinary_message_count == 5
    assert result.summary.undated_ordinary_message_count == 1
    assert result.summary.owner_message_count == 2
    assert result.summary.contact_message_count == 1
    assert result.summary.unknown_direction_message_count == 3
    assert result.summary.undated_unknown_direction_message_count == 1
    assert [month.month for month in result.months] == [
        "2025-01",
        "2025-02",
        "2025-03",
    ]
    assert [
        (month.ordinary_message_count, month.owner_message_count,
         month.contact_message_count, month.unknown_direction_message_count)
        for month in result.months
    ] == [(2, 1, 1, 0), (0, 0, 0, 0), (3, 1, 0, 2)]
    assert result.months[0].active_days == 2
    assert result.months[2].owner_active_days == 1
    assert result.months[2].unknown_direction_active_days == 2


def test_contact_timeline_combines_canonical_sources_and_rejects_unknown_identity(
    db_session,
):
    add_account(db_session, 1, "user-owner-one", username="owner")
    add_account(db_session, 2, "user-owner-two", username="owner_old")
    add_account(db_session, 3, "user-owner-three", username="other")
    add_contact(db_session, 20, 1, "user-shared-peer", "Shared")
    add_contact(db_session, 30, 2, "user-shared-peer", "Shared old")
    add_contact(db_session, 40, 3, "user-other-peer", "Other")
    identity_id = db_session.scalar(
        select(CanonicalIdentity.id).where(
            CanonicalIdentity.platform == "telegram",
            CanonicalIdentity.platform_user_id == "user-shared-peer",
        )
    )
    assert identity_id is not None

    add_chat(db_session, 10, 1, "personal-10", chat_type="personal_chat")
    add_chat(db_session, 20, 2, "personal-20", chat_type="personal_chat")
    add_chat(db_session, 30, 3, "personal-30", chat_type="personal_chat")
    add_chat(db_session, 40, 1, "group-40", chat_type="supergroup")
    add_message(
        db_session,
        1,
        10,
        "message",
        "user-owner-one",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
        is_outgoing=True,
    )
    add_message(
        db_session,
        2,
        10,
        "message",
        "user-shared-peer",
        datetime(2025, 1, 2, tzinfo=timezone.utc),
        is_outgoing=False,
        sender_contact_id=20,
    )
    add_message(
        db_session,
        3,
        10,
        "message",
        "user-other-sender",
        datetime(2025, 1, 3, tzinfo=timezone.utc),
        is_outgoing=False,
    )
    add_message(
        db_session,
        4,
        20,
        "message",
        "user-owner-two",
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        is_outgoing=True,
    )
    add_message(
        db_session,
        5,
        20,
        "message",
        "user-shared-peer",
        datetime(2025, 3, 2, tzinfo=timezone.utc),
        is_outgoing=False,
        sender_contact_id=30,
    )
    add_message(
        db_session,
        7,
        10,
        "message",
        None,
        datetime(2025, 1, 4, tzinfo=timezone.utc),
        is_outgoing=False,
        sender_contact_id=20,
    )
    add_message(
        db_session,
        6,
        30,
        "message",
        "user-other-peer",
        datetime(2025, 2, 1, tzinfo=timezone.utc),
        is_outgoing=False,
        sender_contact_id=40,
    )

    result = CommunicationTimelineStatistics.model_validate(
        get_communication_timeline(db_session, identity_id)
    )

    assert result.summary.scope == "contact"
    assert result.summary.canonical_identity_id == identity_id
    assert result.summary.source_account_ids == [1, 2]
    assert result.summary.source_account_labels == ["@owner", "@owner_old"]
    assert result.summary.source_contact_ids == [20, 30]
    assert result.summary.ordinary_message_count == 6
    assert result.summary.owner_message_count == 2
    assert result.summary.contact_message_count == 3
    assert result.summary.unknown_direction_message_count == 1
    assert [month.month for month in result.months] == [
        "2025-01",
        "2025-02",
        "2025-03",
    ]
    assert [
        (month.owner_message_count, month.contact_message_count,
         month.unknown_direction_message_count)
        for month in result.months
    ] == [(1, 2, 1), (0, 0, 0), (1, 1, 0)]

    with pytest.raises(HTTPException) as error:
        get_communication_timeline(db_session, 9999)
    assert error.value.status_code == 404


def test_chat_timeline_includes_only_the_selected_chat(db_session):
    add_account(db_session, 1, "user-owner", username="owner")
    add_chat(db_session, 10, 1, "chat-10", chat_type="personal_chat")
    add_chat(db_session, 20, 1, "chat-20", chat_type="personal_chat")
    add_message(
        db_session,
        1,
        10,
        "message",
        "user-owner",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
        is_outgoing=True,
    )
    add_message(
        db_session,
        2,
        10,
        "message",
        "user-peer",
        datetime(2025, 1, 2, tzinfo=timezone.utc),
        is_outgoing=False,
    )
    add_message(
        db_session,
        3,
        20,
        "message",
        "user-peer",
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        is_outgoing=False,
    )

    result = CommunicationTimelineStatistics.model_validate(
        get_communication_timeline(db_session, chat_id=10)
    )

    assert result.summary.scope == "chat"
    assert result.summary.chat_id == 10
    assert result.summary.ordinary_message_count == 2
    assert result.summary.owner_message_count == 1
    assert result.summary.contact_message_count == 1
    assert [month.month for month in result.months] == ["2025-01"]
    assert result.summary.source_account_ids == [1]

    with pytest.raises(HTTPException) as error:
        get_communication_timeline(db_session, chat_id=9999)
    assert error.value.status_code == 404


def test_utc_sql_expressions_compile_for_postgresql():
    postgresql_session = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=postgresql.dialect())
    )
    month_sql = str(
        select(_utc_month_expression(postgresql_session, Message.message_date)).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    date_sql = str(
        select(_utc_date_expression(postgresql_session, Message.message_date)).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "to_char(timezone(" in month_sql
    assert "YYYY-MM" in month_sql
    assert "date(timezone(" in date_sql


def test_timeline_endpoint_is_registered():
    assert "/api/analytics/communication-timeline" in app.openapi()["paths"]
