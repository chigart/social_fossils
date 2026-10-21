from datetime import datetime, timedelta, timezone

from analytics_test_helpers import (
    FORGOTTEN_AS_OF,
    HISTORICAL_ACTIVITY_DATES,
    add_account,
    add_contact,
    add_exchanges,
    add_forgotten_candidate,
    add_message,
)

from app.routers.analytics_forgotten_contacts import (
    build_forgotten_contacts_statistics,
)


def test_forgotten_contacts_classifies_and_ranks_by_history_and_decline(db_session):
    add_account(db_session, 1, "user-owner")
    forgotten_chat, forgotten_peer = add_forgotten_candidate(db_session, 20)
    declining_chat, declining_peer = add_forgotten_candidate(db_session, 21)
    active_chat, active_peer = add_forgotten_candidate(db_session, 22)
    little_chat, little_peer = add_forgotten_candidate(db_session, 23)
    add_exchanges(
        db_session,
        20,
        forgotten_chat,
        forgotten_peer,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_exchanges(
        db_session,
        21,
        declining_chat,
        declining_peer,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_exchanges(
        db_session,
        22,
        active_chat,
        active_peer,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_exchanges(
        db_session,
        21,
        declining_chat,
        declining_peer,
        [
            FORGOTTEN_AS_OF - timedelta(days=80),
            FORGOTTEN_AS_OF - timedelta(days=60),
            FORGOTTEN_AS_OF - timedelta(days=30),
        ],
        exchanges_per_day=1,
        message_id_start=100,
    )
    add_exchanges(
        db_session,
        22,
        active_chat,
        active_peer,
        [
            datetime(2026, 8, 1, tzinfo=timezone.utc),
            datetime(2026, 9, 1, tzinfo=timezone.utc),
            FORGOTTEN_AS_OF - timedelta(days=2),
        ],
        exchanges_per_day=5,
        message_id_start=100,
    )
    add_exchanges(
        db_session,
        23,
        little_chat,
        little_peer,
        [
            datetime(2025, 6, 1, tzinfo=timezone.utc),
            datetime(2025, 7, 1, tzinfo=timezone.utc),
        ],
        exchanges_per_day=1,
    )

    result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    by_id = {contact.contact_id: contact for contact in result.contacts}

    assert [contact.contact_id for contact in result.contacts] == [20, 21, 22, 23]
    assert by_id[20].classification == "inactive"
    assert by_id[20].evidence_status == "reliable_baseline"
    assert by_id[20].historical_message_count == 50
    assert by_id[20].recent_message_count == 0
    assert by_id[20].days_since_last_communication == 132
    assert by_id[20].activity_decline_percentage == 100
    assert by_id[20].ranking_score is not None

    assert by_id[21].classification == "activity_declined"
    assert 0 < by_id[21].recent_message_count < by_id[21].historical_message_count
    assert by_id[21].activity_decline_percentage is not None
    assert by_id[21].activity_decline_percentage >= 50
    assert by_id[22].classification == "active"
    assert by_id[22].recent_message_count > 0
    assert by_id[22].activity_decline_percentage == 0
    assert by_id[23].classification == "insufficient_data"
    assert by_id[23].ranking_score is None

    assert result.summary.source_account_count == 1
    assert result.summary.eligible_contacts == 4
    assert result.summary.meaningful_historical_contacts == 3
    assert result.summary.currently_inactive_contacts == 2
    assert result.summary.declining_activity_contacts == 2
    assert result.summary.insufficient_data_contacts == 1

def test_forgotten_contacts_excludes_service_and_counts_normalized_text(db_session):
    add_account(db_session, 1, "user-owner")
    chat_id, peer_id = add_forgotten_candidate(db_session, 20)
    next_message_id = add_exchanges(
        db_session,
        20,
        chat_id,
        peer_id,
        HISTORICAL_ACTIVITY_DATES,
        owner_text="é😀",
        contact_text="x ",
    )
    add_message(
        db_session,
        20 * 10_000 + next_message_id,
        chat_id,
        "message",
        "user-owner",
        is_outgoing=True,
        text_content="",
    )
    add_message(
        db_session,
        20 * 10_000 + next_message_id + 1,
        chat_id,
        "service",
        "user-owner",
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=True,
        text_content="service text must not contribute",
    )
    add_message(
        db_session,
        20 * 10_000 + next_message_id + 2,
        chat_id,
        "service",
        peer_id,
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=False,
        text_content="service text must not contribute",
    )

    result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    contact = result.contacts[0]

    assert contact.owner_message_count == 26
    assert contact.contact_message_count == 25
    assert contact.historical_message_count == 50
    assert contact.owner_text_length == 25 * len("é😀")
    assert contact.contact_text_length == 25 * len("x ")
    assert contact.total_text_length == 100

def test_forgotten_contacts_marks_ambiguous_direction_unscored(db_session):
    add_account(db_session, 1, "user-owner")
    chat_id, peer_id = add_forgotten_candidate(db_session, 20)
    add_exchanges(
        db_session,
        20,
        chat_id,
        peer_id,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_message(
        db_session,
        20 * 10_000 + 100,
        chat_id,
        "message",
        peer_id,
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=None,
    )
    add_message(
        db_session,
        20 * 10_000 + 101,
        chat_id,
        "message",
        None,
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=None,
    )

    contact = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    ).contacts[0]

    assert contact.excluded_ambiguous_message_count == 2
    assert contact.evidence_status == "ambiguous_direction"
    assert contact.classification == "insufficient_data"
    assert contact.ranking_score is None
    assert contact.activity_decline_percentage is None

def test_forgotten_contacts_requires_long_enough_baseline(db_session):
    add_account(db_session, 1, "user-owner")
    chat_id, peer_id = add_forgotten_candidate(db_session, 20)
    dates = [
        datetime(2026, 4, 1, tzinfo=timezone.utc),
        datetime(2026, 4, 15, tzinfo=timezone.utc),
        datetime(2026, 5, 1, tzinfo=timezone.utc),
        datetime(2026, 5, 15, tzinfo=timezone.utc),
        datetime(2026, 6, 1, tzinfo=timezone.utc),
    ]
    add_exchanges(db_session, 20, chat_id, peer_id, dates, exchanges_per_day=10)

    contact = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    ).contacts[0]

    assert contact.historical_message_count == 100
    assert contact.historical_active_days == 5
    assert contact.historical_active_month_count == 3
    assert contact.evidence_status == "insufficient_baseline"
    assert contact.activity_decline_percentage is None
    assert contact.ranking_score is None

def test_forgotten_contacts_splits_partial_cutoff_month_and_orders_ties(db_session):
    add_account(db_session, 1, "user-owner")
    first_chat, first_peer = add_forgotten_candidate(db_session, 20, name="Zed")
    second_chat, second_peer = add_forgotten_candidate(db_session, 21, name="Alex")
    dates = HISTORICAL_ACTIVITY_DATES + [
        datetime(2026, 7, 10, tzinfo=timezone.utc),
    ]
    add_exchanges(db_session, 20, first_chat, first_peer, dates)
    add_exchanges(db_session, 21, second_chat, second_peer, dates)
    for contact_id, chat_id, peer_id in (
        (20, first_chat, first_peer),
        (21, second_chat, second_peer),
    ):
        add_exchanges(
            db_session,
            contact_id,
            chat_id,
            peer_id,
            [datetime(2026, 7, 25, tzinfo=timezone.utc)],
            exchanges_per_day=1,
            message_id_start=100,
        )

    full_result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
        sort_by="historical_message_count",
    )
    limited_result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
        limit=1,
    )
    first = next(c for c in full_result.contacts if c.contact_id == 20)

    assert [contact.contact_id for contact in full_result.contacts] == [20, 21]
    assert [activity.month for activity in first.historical_activity_by_month][-1] == "2026-07"
    assert first.historical_activity_by_month[-1].total_message_count == 10
    assert first.recent_activity_by_month[0].month == "2026-07"
    assert first.recent_activity_by_month[0].total_message_count == 2
    assert limited_result.summary.eligible_contacts == 2
    assert [contact.contact_id for contact in limited_result.contacts] == [20]

def test_forgotten_contacts_does_not_use_missing_timestamps_as_baseline(db_session):
    add_account(db_session, 1, "user-owner")
    chat_id, peer_id = add_forgotten_candidate(db_session, 20)
    add_exchanges(
        db_session,
        20,
        chat_id,
        peer_id,
        [None],
        exchanges_per_day=1,
    )

    contact = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    ).contacts[0]

    assert contact.total_message_count == 2
    assert contact.first_message_at is None
    assert contact.last_message_at is None
    assert contact.days_since_last_communication is None
    assert contact.historical_message_count == 0
    assert contact.evidence_status == "insufficient_history"
    assert contact.classification == "insufficient_data"
    assert contact.ranking_score is None

def test_forgotten_contacts_excludes_groups_and_multiple_peer_chats(db_session):
    add_account(db_session, 1, "user-owner")
    group_chat, group_peer = add_forgotten_candidate(
        db_session,
        20,
        chat_type="supergroup",
    )
    add_exchanges(
        db_session,
        20,
        group_chat,
        group_peer,
        HISTORICAL_ACTIVITY_DATES,
    )

    chat_id, peer_id = add_forgotten_candidate(db_session, 21)
    third_peer_id = "user-third-peer"
    add_contact(db_session, 31, 1, third_peer_id, "Third peer")
    add_exchanges(
        db_session,
        21,
        chat_id,
        peer_id,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_message(
        db_session,
        21 * 10_000 + 100,
        chat_id,
        "message",
        third_peer_id,
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=False,
        sender_contact_id=31,
    )

    result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )

    assert result.summary.eligible_contacts == 0
    assert result.contacts == []

def test_forgotten_contacts_combines_owner_aliases_and_canonical_contacts(db_session):
    add_account(db_session, 1, "user-owner-one", username="anton")
    add_account(db_session, 2, "user-owner-two", username="anton_old")
    for account_id, contact_id in ((1, 20), (2, 30)):
        chat_id, peer_id = add_forgotten_candidate(
            db_session,
            contact_id,
            account_id=account_id,
            peer_id="user-shared-telegram-peer",
        )
        add_exchanges(
            db_session,
            contact_id,
            chat_id,
            peer_id,
            HISTORICAL_ACTIVITY_DATES,
            owner_id=f"user-owner-{'one' if account_id == 1 else 'two'}",
        )

    add_message(
        db_session,
        200051,
        10020,
        "message",
        "user-owner-two",
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=False,
    )
    result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    assert len(result.contacts) == 1
    assert result.contacts[0].total_message_count == 101
    assert result.contacts[0].owner_message_count == 51
    assert result.contacts[0].contact_message_count == 50
    assert result.contacts[0].source_account_ids == [1, 2]
    assert result.contacts[0].source_account_labels == ["@anton", "@anton_old"]
    assert result.contacts[0].source_contact_ids == [20, 30]
    assert result.contacts[0].account_id is None
    assert result.summary.source_account_count == 2
    assert result.summary.scope == "combined_owner"

def test_forgotten_contacts_empty_database_and_account_without_private_chats(
    db_session,
):
    empty_result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    assert empty_result.summary.source_account_count == 0
    assert empty_result.summary.eligible_contacts == 0
    assert empty_result.contacts == []

    add_account(db_session, 1, "user-owner")
    group_chat, group_peer = add_forgotten_candidate(
        db_session,
        20,
        chat_type="group",
    )
    add_exchanges(
        db_session,
        20,
        group_chat,
        group_peer,
        HISTORICAL_ACTIVITY_DATES,
    )
    no_private_results = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    assert no_private_results.summary.source_account_count == 1
    assert no_private_results.summary.eligible_contacts == 0
    assert no_private_results.contacts == []
