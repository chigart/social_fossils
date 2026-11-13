from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Account,
    CanonicalIdentity,
    CanonicalIdentityGroup,
    Contact,
    IdentityLinkEvent,
)
from app.schemas.identity_links import (
    IdentityLinkActionResponse,
    IdentityLinkEventView,
    IdentityLinkRequest,
    IdentityLinksResponse,
    IdentityContactSource,
    PlatformIdentityView,
    UnidentifiedContactView,
)

router = APIRouter(prefix="/api/identity-links", tags=["identity links"])


def _owner_identity_keys(db: Session) -> set[tuple[str, str]]:
    return {
        (platform, platform_user_id)
        for platform, platform_user_id in db.execute(
            select(Account.platform, Account.platform_user_id).where(
                Account.platform_user_id.is_not(None)
            )
        ).all()
        if platform_user_id is not None
    }


def _contact_source(contact: Contact, account: Account) -> IdentityContactSource:
    return IdentityContactSource(
        contact_id=contact.id,
        account_id=account.id,
        account_label=account.username or account.name,
        platform=contact.platform,
        display_name=contact.display_name,
        username=contact.username,
    )


def _identity_links_response(db: Session) -> IdentityLinksResponse:
    owner_identity_keys = _owner_identity_keys(db)
    identities = db.scalars(
        select(CanonicalIdentity).order_by(
            CanonicalIdentity.platform,
            CanonicalIdentity.platform_user_id,
        )
    ).all()
    contact_rows = db.execute(
        select(Contact, Account)
        .join(Account, Account.id == Contact.account_id)
        .order_by(Contact.account_id, Contact.id)
    ).all()

    sources_by_identity: dict[int, list[IdentityContactSource]] = {}
    unidentified_contacts: list[UnidentifiedContactView] = []
    for contact, account in contact_rows:
        if contact.canonical_identity_id is None:
            unidentified_contacts.append(
                UnidentifiedContactView(
                    contact_id=contact.id,
                    account_id=account.id,
                    account_label=account.username or account.name,
                    platform=contact.platform,
                    display_name=contact.display_name,
                    username=contact.username,
                )
            )
            continue
        sources_by_identity.setdefault(contact.canonical_identity_id, []).append(
            _contact_source(contact, account)
        )

    events = db.scalars(
        select(IdentityLinkEvent).order_by(
            IdentityLinkEvent.occurred_at.desc(),
            IdentityLinkEvent.id.desc(),
        )
    ).all()
    return IdentityLinksResponse(
        identities=[
            PlatformIdentityView(
                identity_id=identity.id,
                platform=identity.platform,
                platform_user_id=identity.platform_user_id,
                identity_group_id=identity.identity_group_id,
                is_owner=(
                    identity.platform,
                    identity.platform_user_id,
                ) in owner_identity_keys,
                contacts=sources_by_identity.get(identity.id, []),
            )
            for identity in identities
        ],
        contacts_without_identity=unidentified_contacts,
        events=[
            IdentityLinkEventView(
                id=event.id,
                group_id=event.group_id,
                identity_id=event.identity_id,
                peer_identity_id=event.peer_identity_id,
                action=event.action,
                source=event.source,
                occurred_at=event.occurred_at,
            )
            for event in events
        ],
    )


@router.get("", response_model=IdentityLinksResponse)
def get_identity_links(db: Session = Depends(get_db)) -> IdentityLinksResponse:
    return _identity_links_response(db)


@router.post(
    "",
    response_model=IdentityLinkActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_identities(
    request: IdentityLinkRequest,
    db: Session = Depends(get_db),
) -> IdentityLinkActionResponse:
    if request.first_identity_id == request.second_identity_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose two different platform identities.",
        )

    first = db.get(CanonicalIdentity, request.first_identity_id)
    second = db.get(CanonicalIdentity, request.second_identity_id)
    if first is None or second is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform identity not found.",
        )
    owner_identity_keys = _owner_identity_keys(db)
    if any(
        (identity.platform, identity.platform_user_id) in owner_identity_keys
        for identity in (first, second)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner accounts cannot be linked to contacts.",
        )
    if (
        first.identity_group_id is not None
        and first.identity_group_id == second.identity_group_id
    ):
        return IdentityLinkActionResponse(
            status="linked",
            identity_group_id=first.identity_group_id,
        )
    group_id = first.identity_group_id or second.identity_group_id
    if group_id is None:
        group = CanonicalIdentityGroup()
        db.add(group)
        db.flush()
        group_id = group.id

    first_was_grouped = first.identity_group_id is not None
    second_group_id = second.identity_group_id
    if second_group_id is not None and second_group_id != group_id:
        members_to_merge = db.scalars(
            select(CanonicalIdentity).where(
                CanonicalIdentity.identity_group_id == second_group_id
            )
        ).all()
        for member in members_to_merge:
            member.identity_group_id = group_id
        group_to_remove = db.get(CanonicalIdentityGroup, second_group_id)
        if group_to_remove is not None:
            db.delete(group_to_remove)

    first.identity_group_id = group_id
    second.identity_group_id = group_id
    db.add(
        IdentityLinkEvent(
            group_id=group_id,
            identity_id=second.id if first_was_grouped else first.id,
            peer_identity_id=first.id if first_was_grouped else second.id,
            action="linked",
            source="dashboard",
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This identity link conflicts with an existing assignment.",
        ) from exc
    return IdentityLinkActionResponse(
        status="linked",
        identity_group_id=group_id,
    )


@router.delete(
    "/{identity_id}",
    response_model=IdentityLinkActionResponse,
)
def unlink_identity(
    identity_id: int,
    db: Session = Depends(get_db),
) -> IdentityLinkActionResponse:
    identity = db.get(CanonicalIdentity, identity_id)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform identity not found.",
        )
    group_id = identity.identity_group_id
    if group_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This platform identity is not linked.",
        )

    members = db.scalars(
        select(CanonicalIdentity)
        .where(CanonicalIdentity.identity_group_id == group_id)
        .order_by(CanonicalIdentity.id)
    ).all()
    peer = next((member for member in members if member.id != identity.id), None)
    db.add(
        IdentityLinkEvent(
            group_id=group_id,
            identity_id=identity.id,
            peer_identity_id=peer.id if peer is not None else None,
            action="unlinked",
            source="dashboard",
        )
    )
    identity.identity_group_id = None

    remaining = [member for member in members if member.id != identity.id]
    if len(remaining) < 2:
        for member in remaining:
            member.identity_group_id = None
        group = db.get(CanonicalIdentityGroup, group_id)
        if group is not None:
            db.delete(group)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The identity link changed before it could be removed.",
        ) from exc
    return IdentityLinkActionResponse(status="unlinked")
