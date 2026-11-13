from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IdentityContactSource(BaseModel):
    contact_id: int
    account_id: int
    account_label: str
    platform: str
    display_name: str | None
    username: str | None


class PlatformIdentityView(BaseModel):
    identity_id: int
    platform: str
    platform_user_id: str
    identity_group_id: int | None
    is_owner: bool = False
    contacts: list[IdentityContactSource] = Field(default_factory=list)


class UnidentifiedContactView(BaseModel):
    contact_id: int
    account_id: int
    account_label: str
    platform: str
    display_name: str | None
    username: str | None


class IdentityLinkEventView(BaseModel):
    id: int
    group_id: int | None
    identity_id: int
    peer_identity_id: int | None
    action: Literal["linked", "unlinked"]
    source: str
    occurred_at: datetime


class IdentityLinksResponse(BaseModel):
    identities: list[PlatformIdentityView]
    contacts_without_identity: list[UnidentifiedContactView]
    events: list[IdentityLinkEventView]


class IdentityLinkRequest(BaseModel):
    first_identity_id: int = Field(gt=0)
    second_identity_id: int = Field(gt=0)


class IdentityLinkActionResponse(BaseModel):
    status: Literal["linked", "unlinked"]
    identity_group_id: int | None = None
