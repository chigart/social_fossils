from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from analytics_test_helpers import add_account, add_chat, add_contact, add_message
from app.routers.analytics_friendship import (
    FriendshipAnalytics,
    build_friendship_analytics,
)
from app.routers.analytics_contacts import get_contact_statistics
from app.schemas.analytics import CloseFriendsTimelineStatistics


def _add_text_exchange(
    db_session,
    *,
    message_id: int,
    chat_id: int,
    contact_id: int,
    peer_id: str,
    message_date: datetime,
) -> int:
    add_message(
        db_session,
        message_id,
        chat_id,
        "message",
        "user-owner",
        message_date=message_date,
        is_outgoing=True,
        text_content="owner",
    )
    add_message(
        db_session,
        message_id + 1,
        chat_id,
        "message",
        peer_id,
        message_date=message_date,
        is_outgoing=False,
        sender_contact_id=contact_id,
        text_content="peer",
    )
    return message_id + 2


def test_friend_statuses_and_close_timeline_use_full_years_and_owner_continuity(
    db_session,
):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "active-close", chat_type="personal_chat")
    add_chat(db_session, 20, 1, "former-close", chat_type="personal_chat")
    add_chat(db_session, 30, 1, "partial-first-year", chat_type="personal_chat")
    add_chat(db_session, 40, 1, "group-only", chat_type="private_group")
    add_chat(db_session, 50, 1, "active-below-threshold", chat_type="personal_chat")
    add_chat(db_session, 60, 1, "close-below-threshold", chat_type="personal_chat")
    add_contact(db_session, 11, 1, "user-active-close", "Active close")
    add_contact(db_session, 21, 1, "user-former-close", "Former close")
    add_contact(db_session, 31, 1, "user-partial", "Partial first year")
    add_contact(db_session, 41, 1, "user-group-only", "Group only")
    add_contact(db_session, 51, 1, "user-active-below", "Active below threshold")
    add_contact(db_session, 61, 1, "user-close-below", "Close below threshold")

    next_id = 1
    for index in range(100):
        next_id = _add_text_exchange(
            db_session,
            message_id=next_id,
            chat_id=10,
            contact_id=11,
            peer_id="user-active-close",
            message_date=(
                datetime(2020, 12, 31, tzinfo=timezone.utc)
                if index == 99
                else datetime(2020, 1, 1, tzinfo=timezone.utc)
                + timedelta(days=index)
            ),
        )

    for index in range(100):
        next_id = _add_text_exchange(
            db_session,
            message_id=next_id,
            chat_id=20,
            contact_id=21,
            peer_id="user-former-close",
            message_date=(
                datetime(2020, 12, 31, tzinfo=timezone.utc)
                if index == 99
                else datetime(2020, 1, 1, tzinfo=timezone.utc)
                + timedelta(days=index)
            ),
        )

    for index in range(50):
        next_id = _add_text_exchange(
            db_session,
            message_id=next_id,
            chat_id=30,
            contact_id=31,
            peer_id="user-partial",
            message_date=datetime(2019, 6, 1, tzinfo=timezone.utc)
            + timedelta(days=index),
        )
    for index in range(50):
        next_id = _add_text_exchange(
            db_session,
            message_id=next_id,
            chat_id=40,
            contact_id=41,
            peer_id="user-group-only",
            message_date=datetime(2020, 3, 1, tzinfo=timezone.utc)
            + timedelta(days=index),
        )
    for index in range(10):
        next_id = _add_text_exchange(
            db_session,
            message_id=next_id,
            chat_id=10,
            contact_id=11,
            peer_id="user-active-close",
            message_date=datetime(2021, 1, 15, tzinfo=timezone.utc),
        )
    for index in range(10):
        next_id = _add_text_exchange(
            db_session,
            message_id=next_id,
            chat_id=10,
            contact_id=11,
            peer_id="user-active-close",
            message_date=datetime(2022, 3, 1, tzinfo=timezone.utc)
            + timedelta(days=index),
        )
    for index in range(4):
        next_id = _add_text_exchange(
            db_session,
            message_id=next_id,
            chat_id=50,
            contact_id=51,
            peer_id="user-active-below",
            message_date=datetime(2022, 3, 1, tzinfo=timezone.utc)
            + timedelta(days=index),
        )
    add_message(
        db_session,
        next_id,
        50,
        "message",
        "user-owner",
        message_date=datetime(2022, 3, 5, tzinfo=timezone.utc),
        is_outgoing=True,
        text_content="owner",
    )
    next_id += 1
    for index in range(49):
        next_id = _add_text_exchange(
            db_session,
            message_id=next_id,
            chat_id=60,
            contact_id=61,
            peer_id="user-close-below",
            message_date=datetime(2020, 2, 1, tzinfo=timezone.utc)
            + timedelta(days=index),
        )
    add_message(
        db_session,
        next_id,
        60,
        "message",
        "user-owner",
        message_date=datetime(2020, 12, 31, tzinfo=timezone.utc),
        is_outgoing=True,
        text_content="owner",
    )

    contacts = get_contact_statistics(db_session).items
    active_close = next(
        contact
        for contact in contacts
        if "user-active-close" in contact.platform_user_ids
    )
    former_close = next(
        contact
        for contact in contacts
        if "user-former-close" in contact.platform_user_ids
    )
    partial_first_year = next(
        contact for contact in contacts if "user-partial" in contact.platform_user_ids
    )
    group_only = next(
        contact
        for contact in contacts
        if "user-group-only" in contact.platform_user_ids
    )
    active_below = next(
        contact
        for contact in contacts
        if "user-active-below" in contact.platform_user_ids
    )
    close_below = next(
        contact
        for contact in contacts
        if "user-close-below" in contact.platform_user_ids
    )

    assert active_close.friend_statuses == ["exClose"]
    assert former_close.friend_statuses == ["exClose"]
    assert partial_first_year.friend_statuses == []
    assert group_only.friend_statuses == []
    assert active_below.friend_statuses == []
    assert close_below.friend_statuses == []

    friendship = build_friendship_analytics(
        db_session,
        as_of=datetime(2022, 6, 30, tzinfo=timezone.utc),
    )

    assert friendship.statuses_by_contact[
        ("identity", active_close.canonical_identity_id)
    ] == ["Active", "Close"]
    assert friendship.statuses_by_contact[
        ("identity", former_close.canonical_identity_id)
    ] == ["exClose"]
    assert ("identity", partial_first_year.canonical_identity_id) not in (
        friendship.statuses_by_contact
    )
    assert ("identity", group_only.canonical_identity_id) not in (
        friendship.statuses_by_contact
    )
    assert ("identity", active_below.canonical_identity_id) not in (
        friendship.statuses_by_contact
    )
    assert ("identity", close_below.canonical_identity_id) not in (
        friendship.statuses_by_contact
    )
    assert [
        (year.year, year.close_friend_count) for year in friendship.timeline.years
    ] == [
        (2020, 2),
        (2021, 1),
        (2022, 1),
    ]


def test_friendship_history_combines_explicitly_linked_platform_identities(
    db_session,
):
    add_account(db_session, 1, "telegram-owner")
    add_account(db_session, 2, "instagram-owner")
    add_chat(db_session, 10, 1, "telegram-chat", chat_type="personal_chat")
    add_chat(db_session, 20, 2, "instagram-chat", chat_type="personal_chat")
    add_contact(db_session, 11, 1, "telegram-peer", "Linked peer")
    add_contact(db_session, 21, 2, "instagram-peer", "Linked peer")
    db_session.execute(
        text(
            "UPDATE account SET platform = 'instagram' WHERE id = 2"
        )
    )
    db_session.execute(
        text(
            "UPDATE chats SET platform = 'instagram' WHERE id = 20"
        )
    )
    db_session.execute(
        text(
            "UPDATE contacts SET platform = 'instagram' WHERE id = 21"
        )
    )
    db_session.execute(
        text(
            "UPDATE canonical_identities SET platform = 'instagram', "
            "identity_group_id = 77 WHERE platform_user_id = 'instagram-peer'"
        )
    )
    db_session.execute(
        text(
            "UPDATE canonical_identities SET identity_group_id = 77 "
            "WHERE platform_user_id = 'telegram-peer'"
        )
    )

    next_id = 1
    for chat_id, contact_id, peer_id, owner_id, platform in [
        (10, 11, "telegram-peer", "telegram-owner", "telegram"),
        (20, 21, "instagram-peer", "instagram-owner", "instagram"),
    ]:
        for index in range(50):
            message_date = (
                datetime(2020, 12, 31, tzinfo=timezone.utc)
                if index == 49
                else datetime(2020, 1, 1, tzinfo=timezone.utc)
                + timedelta(days=index)
            )
            _add_text_exchange(
                db_session,
                message_id=next_id,
                chat_id=chat_id,
                contact_id=contact_id,
                peer_id=peer_id,
                message_date=message_date,
            )
            db_session.execute(
                text("UPDATE messages SET platform = :platform WHERE chat_id = :chat_id"),
                {"platform": platform, "chat_id": chat_id},
            )
            db_session.execute(
                text(
                    "UPDATE messages SET sender_id = :owner_id "
                    "WHERE chat_id = :chat_id AND sender_id = 'user-owner'"
                ),
                {"owner_id": owner_id, "chat_id": chat_id},
            )
            next_id += 2

    friendship = build_friendship_analytics(
        db_session,
        as_of=datetime(2021, 6, 30, tzinfo=timezone.utc),
    )

    assert friendship.statuses_by_contact[("group", 77)] == ["Close"]
    assert [(year.year, year.close_friend_count) for year in friendship.timeline.years] == [
        (2020, 1),
    ]


def test_contact_friend_status_filter_applies_before_pagination(
    db_session,
    monkeypatch,
):
    add_account(db_session, 1, "user-owner")
    add_contact(db_session, 11, 1, "peer-one", "Peer One")
    add_contact(db_session, 12, 1, "peer-two", "Peer Two")
    peer_one_identity = db_session.scalar(
        text(
            "SELECT id FROM canonical_identities WHERE platform_user_id = 'peer-one'"
        )
    )
    peer_two_identity = db_session.scalar(
        text(
            "SELECT id FROM canonical_identities WHERE platform_user_id = 'peer-two'"
        )
    )
    monkeypatch.setattr(
        "app.routers.analytics_contacts.build_friendship_analytics",
        lambda _db: FriendshipAnalytics(
            statuses_by_contact={
                ("identity", peer_one_identity): ["Active", "Close"],
                ("identity", peer_two_identity): ["exClose"],
            },
            timeline=CloseFriendsTimelineStatistics(years=[]),
        ),
    )

    close_contacts = get_contact_statistics(
        db_session,
        friend_status="Close",
        page_size=1,
    )

    assert close_contacts.pagination.total == 1
    assert [contact.display_name for contact in close_contacts.items] == ["Peer One"]
    assert close_contacts.items[0].friend_statuses == ["Active", "Close"]
