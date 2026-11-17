from app.main import app
from app.routers.analytics_communication_balance import get_communication_balance
from app.routers.analytics_contacts import get_contact_statistics
from app.routers.analytics_overview import get_chat_statistics, get_overview
from app.schemas.analytics import (
    CommunicationBalanceStatistics,
    OverviewStatistics,
)


def test_empty_database_returns_zeroes_and_empty_lists(db_session):
    overview = get_overview(db_session)

    assert OverviewStatistics.model_validate(overview).model_dump() == {
        "total_imported_accounts": 0,
        "total_chats": 0,
        "total_messages": 0,
        "total_ordinary_messages": 0,
        "total_service_messages": 0,
        "imported_accounts": [],
        "earliest_message_timestamp": None,
        "latest_message_timestamp": None,
    }
    assert get_chat_statistics(db_session).items == []
    assert get_contact_statistics(db_session).items == []
    balance = CommunicationBalanceStatistics.model_validate(
        get_communication_balance(db_session)
    )
    assert balance.summary.eligible_contacts == 0
    assert balance.contacts == []
    assert set(app.openapi()["paths"]) >= {
        "/api/analytics/overview",
        "/api/analytics/chats",
        "/api/analytics/contacts",
        "/api/analytics/communication-balance",
        "/api/analytics/forgotten-contacts",
        "/api/analytics/close-friends-timeline",
        "/api/analytics/owner-reply-timeline",
    }
    forgotten_parameters = app.openapi()["paths"][
        "/api/analytics/forgotten-contacts"
    ]["get"]["parameters"]
    assert all(parameter["name"] != "account_id" for parameter in forgotten_parameters)
