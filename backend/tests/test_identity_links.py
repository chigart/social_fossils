from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base, get_db
from app.main import app
from app.models import (
    Account,
    CanonicalIdentity,
    CanonicalIdentityGroup,
    Contact,
    IdentityLinkEvent,
)


def _create_identity_tables(engine) -> None:
    Base.metadata.create_all(
        engine,
        tables=[
            Account.__table__,
            CanonicalIdentityGroup.__table__,
            CanonicalIdentity.__table__,
            Contact.__table__,
            IdentityLinkEvent.__table__,
        ],
    )


def test_identity_links_reject_conflicts_and_preserve_link_history(tmp_path):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'identity-links.db'}",
        connect_args={"check_same_thread": False},
    )
    _create_identity_tables(engine)
    session = Session(engine)
    account = Account(
        platform="telegram",
        name="Synthetic account",
        platform_user_id="owner",
    )
    session.add(account)
    session.flush()
    identities = [
        CanonicalIdentity(platform="telegram", platform_user_id="telegram-1"),
        CanonicalIdentity(platform="instagram", platform_user_id="instagram-1"),
        CanonicalIdentity(platform="telegram", platform_user_id="telegram-2"),
        CanonicalIdentity(platform="instagram", platform_user_id="instagram-2"),
    ]
    session.add_all(identities)
    session.flush()
    session.add(
        Contact(
            account_id=account.id,
            platform="instagram",
            platform_user_id=None,
            source_contact_key="a" * 64,
            canonical_identity_id=None,
            display_name="Synthetic unidentified contact",
        )
    )
    session.commit()
    identity_ids = [identity.id for identity in identities]

    def override_get_db():
        yield session

    with TestClient(app) as client:
        app.dependency_overrides[get_db] = override_get_db
        try:
            initial = client.get("/api/identity-links")
            assert initial.status_code == 200
            assert len(initial.json()["identities"]) == 4
            assert initial.json()["contacts_without_identity"][0][
                "display_name"
            ] == "Synthetic unidentified contact"

            first_link = client.post(
                "/api/identity-links",
                json={
                    "first_identity_id": identity_ids[0],
                    "second_identity_id": identity_ids[1],
                },
            )
            second_link = client.post(
                "/api/identity-links",
                json={
                    "first_identity_id": identity_ids[2],
                    "second_identity_id": identity_ids[3],
                },
            )
            assert first_link.status_code == 201
            assert second_link.status_code == 201
            assert (
                first_link.json()["identity_group_id"]
                != second_link.json()["identity_group_id"]
            )

            conflict = client.post(
                "/api/identity-links",
                json={
                    "first_identity_id": identity_ids[0],
                    "second_identity_id": identity_ids[3],
                },
            )
            assert conflict.status_code == 409

            unlink = client.delete(f"/api/identity-links/{identity_ids[0]}")
            assert unlink.status_code == 200
            assert unlink.json()["status"] == "unlinked"

            linked_state = client.get("/api/identity-links").json()
            groups_by_id = {
                identity["identity_id"]: identity["identity_group_id"]
                for identity in linked_state["identities"]
            }
            assert groups_by_id[identity_ids[0]] is None
            assert groups_by_id[identity_ids[1]] is None
            assert (
                groups_by_id[identity_ids[2]]
                == groups_by_id[identity_ids[3]]
            )
            assert [event["action"] for event in linked_state["events"]].count(
                "linked"
            ) == 2
            assert linked_state["events"][0]["action"] == "unlinked"
            assert linked_state["events"][0]["source"] == "dashboard"

            history = session.scalars(
                select(IdentityLinkEvent).order_by(IdentityLinkEvent.id)
            ).all()
            assert len(history) == 3
            assert history[0].peer_identity_id == identity_ids[1]
            assert history[-1].action == "unlinked"
        finally:
            app.dependency_overrides.pop(get_db, None)
            session.close()
            engine.dispose()


def test_identity_links_allow_any_number_of_same_platform_accounts(tmp_path):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'multi-account-identity-links.db'}",
        connect_args={"check_same_thread": False},
    )
    _create_identity_tables(engine)
    session = Session(engine)
    identities = [
        CanonicalIdentity(platform="telegram", platform_user_id="telegram-1"),
        CanonicalIdentity(platform="telegram", platform_user_id="telegram-2"),
        CanonicalIdentity(platform="instagram", platform_user_id="instagram-1"),
        CanonicalIdentity(platform="instagram", platform_user_id="instagram-2"),
        CanonicalIdentity(platform="discord", platform_user_id="discord-1"),
    ]
    session.add_all(identities)
    session.commit()
    identity_ids = [identity.id for identity in identities]

    def override_get_db():
        yield session

    with TestClient(app) as client:
        app.dependency_overrides[get_db] = override_get_db
        try:
            links = [
                (identity_ids[0], identity_ids[1]),
                (identity_ids[0], identity_ids[2]),
                (identity_ids[1], identity_ids[3]),
                (identity_ids[2], identity_ids[4]),
            ]
            responses = [
                client.post(
                    "/api/identity-links",
                    json={
                        "first_identity_id": first_id,
                        "second_identity_id": second_id,
                    },
                )
                for first_id, second_id in links
            ]

            assert [response.status_code for response in responses] == [201] * 4
            group_ids = {
                response.json()["identity_group_id"] for response in responses
            }
            assert len(group_ids) == 1
            grouped_id = group_ids.pop()
            linked_identities = client.get("/api/identity-links").json()[
                "identities"
            ]
            assert {
                identity["identity_id"]: identity["identity_group_id"]
                for identity in linked_identities
            } == {identity_id: grouped_id for identity_id in identity_ids}
        finally:
            app.dependency_overrides.pop(get_db, None)
            session.close()
            engine.dispose()
