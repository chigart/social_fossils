from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import DEFAULT_PAGE_SIZE
from app.db import get_db
from app.models import Account
from app.schemas.analytics import (
    ForgottenContact,
    ForgottenContactEvidenceStatus,
    ForgottenContactMonthlyActivity,
    ForgottenContactsStatistics,
    ForgottenContactsSummary,
    PaginationMetadata,
    SearchOption,
)

from .analytics_forgotten_queries import (
    build_forgotten_contact_queries,
)

from app.constants import (
    FORGOTTEN_RECENT_WINDOW_DAYS,
    FORGOTTEN_INACTIVE_DAYS,
    FORGOTTEN_MIN_HISTORICAL_MESSAGES,
    FORGOTTEN_MIN_HISTORICAL_ACTIVE_DAYS,
    FORGOTTEN_MIN_HISTORICAL_ACTIVE_MONTHS,
    FORGOTTEN_MIN_BASELINE_SPAN_DAYS,
    FORGOTTEN_DECLINE_THRESHOLD,
    FORGOTTEN_RECENT_MONTH_DAYS,
    FORGOTTEN_EVIDENCE_MESSAGE_CAP,
    FORGOTTEN_SCORE_INACTIVITY_CAP_DAYS,
    FORGOTTEN_SCORE_INACTIVITY_WEIGHT,
    FORGOTTEN_SCORE_DECLINE_WEIGHT,
    FORGOTTEN_MAX_LIMIT,
)

router = APIRouter()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_forgotten_contacts_statistics(
    db: Session,
    *,
    scope: Literal["private", "group"] = "private",
    sort_by: Literal[
        "ranking_score",
        "display_name",
        "days_since_last_communication",
        "historical_message_count",
    ] = "ranking_score",
    sort_direction: Literal["asc", "desc"] = "desc",
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    as_of: datetime | None = None,
    platform: str | None = None,
) -> ForgottenContactsStatistics:
    if not 1 <= limit <= FORGOTTEN_MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {FORGOTTEN_MAX_LIMIT}.")
    if offset < 0:
        raise ValueError("offset must be non-negative.")

    source_account_count = int(
        db.scalar(
            select(func.count(Account.id))
        )
        or 0
    )
    if source_account_count == 0:
        return ForgottenContactsStatistics(
            summary=ForgottenContactsSummary(
                source_account_count=0,
                eligible_contacts=0,
                meaningful_historical_contacts=0,
                currently_inactive_contacts=0,
                declining_activity_contacts=0,
                insufficient_data_contacts=0,
            ),
            contacts=[],
            pagination=PaginationMetadata(
                page=offset // limit + 1,
                page_size=limit,
                total=0,
            ),
        )

    current_time = _as_utc(as_of or datetime.now(timezone.utc))
    recent_start = current_time - timedelta(days=FORGOTTEN_RECENT_WINDOW_DAYS)
    eligible_pairs, aggregate_statement, monthly_statement = (
        build_forgotten_contact_queries(
            db,
            recent_start,
            current_time,
            scope,
        )
    )

    monthly_by_contact: dict[
        tuple[int | None, int | None, int | None, int | None],
        list[dict[str, int | str]],
    ] = {}
    for month_row in db.execute(monthly_statement):
        monthly_by_contact.setdefault(
            (
                month_row.identity_group_id,
                month_row.canonical_identity_id,
                month_row.identity_contact_id,
                month_row.identity_source_account_id,
            ),
            [],
        ).append(
            {
                "month": month_row.month,
                "historical_owner_message_count": int(
                    month_row.historical_owner_message_count
                ),
                "historical_contact_message_count": int(
                    month_row.historical_contact_message_count
                ),
                "recent_owner_message_count": int(
                    month_row.recent_owner_message_count
                ),
                "recent_contact_message_count": int(
                    month_row.recent_contact_message_count
                ),
            }
        )

    source_rows = db.execute(
        select(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.canonical_identity_id,
            eligible_pairs.c.identity_contact_id,
            eligible_pairs.c.identity_source_account_id,
            eligible_pairs.c.account_id,
            eligible_pairs.c.contact_id,
            eligible_pairs.c.platform,
            eligible_pairs.c.contact_platform_user_id,
            Account.username.label("account_username"),
            Account.name.label("account_name"),
        ).distinct()
        .join(Account, Account.id == eligible_pairs.c.account_id)
    )
    source_ids: dict[
        tuple[int | None, int | None, int | None, int | None],
        tuple[set[int], set[int], set[str], set[str], set[str], set[int]],
    ] = {}
    for source_row in source_rows:
        key = (
            source_row.identity_group_id,
            source_row.canonical_identity_id,
            source_row.identity_contact_id,
            source_row.identity_source_account_id,
        )
        (
            accounts,
            contact_ids,
            account_labels,
            platforms,
            platform_user_ids,
            identity_ids,
        ) = source_ids.setdefault(
            key, (set(), set(), set(), set(), set(), set())
        )
        accounts.add(source_row.account_id)
        contact_ids.add(source_row.contact_id)
        platforms.add(source_row.platform)
        platform_user_ids.add(source_row.contact_platform_user_id)
        if source_row.canonical_identity_id is not None:
            identity_ids.add(source_row.canonical_identity_id)
        account_labels.add(
            f"@{source_row.account_username}"
            if source_row.account_username
            else source_row.account_name
        )

    contacts: list[ForgottenContact] = []
    for row in db.execute(aggregate_statement):
        owner_message_count = int(row.owner_message_count)
        contact_message_count = int(row.contact_message_count)
        owner_text_length = int(row.owner_text_length)
        contact_text_length = int(row.contact_text_length)
        recent_owner_count = int(row.recent_owner_message_count)
        recent_contact_count = int(row.recent_contact_message_count)
        recent_count = recent_owner_count + recent_contact_count
        historical_count = int(row.historical_message_count)
        excluded_ambiguous_count = (
            int(row.ordinary_message_count) - int(row.known_message_count)
        )
        first_message_at = (
            _as_utc(row.first_message_at) if row.first_message_at is not None else None
        )
        last_message_at = (
            _as_utc(row.last_message_at) if row.last_message_at is not None else None
        )
        historical_first = (
            _as_utc(row.historical_first_message_at)
            if row.historical_first_message_at is not None
            else None
        )
        historical_last = (
            _as_utc(row.historical_last_message_at)
            if row.historical_last_message_at is not None
            else None
        )
        days_since_last = (
            max(0, (current_time - last_message_at).days)
            if last_message_at is not None
            else None
        )

        historical_months: list[ForgottenContactMonthlyActivity] = []
        recent_months: list[ForgottenContactMonthlyActivity] = []
        group_key = (
            row.identity_group_id,
            row.canonical_identity_id,
            row.identity_contact_id,
            row.identity_source_account_id,
        )
        monthly_rows = monthly_by_contact.get(group_key, [])
        historical_active_month_count = 0
        for month_row in monthly_rows:
            historical_owner = int(month_row["historical_owner_message_count"])
            historical_contact = int(month_row["historical_contact_message_count"])
            recent_owner = int(month_row["recent_owner_message_count"])
            recent_contact = int(month_row["recent_contact_message_count"])
            historical_total = historical_owner + historical_contact
            recent_total = recent_owner + recent_contact
            if historical_total:
                historical_active_month_count += 1
                historical_months.append(
                    ForgottenContactMonthlyActivity(
                        month=str(month_row["month"]),
                        owner_message_count=historical_owner,
                        contact_message_count=historical_contact,
                        total_message_count=historical_total,
                    )
                )
            if recent_total:
                recent_months.append(
                    ForgottenContactMonthlyActivity(
                        month=str(month_row["month"]),
                        owner_message_count=recent_owner,
                        contact_message_count=recent_contact,
                        total_message_count=recent_total,
                    )
                )

        meaningful_history = (
            historical_count >= FORGOTTEN_MIN_HISTORICAL_MESSAGES
            and int(row.historical_active_days)
            >= FORGOTTEN_MIN_HISTORICAL_ACTIVE_DAYS
            and historical_active_month_count
            >= FORGOTTEN_MIN_HISTORICAL_ACTIVE_MONTHS
        )
        historical_span_days = (
            (historical_last - historical_first).total_seconds() / 86400
            if historical_first is not None and historical_last is not None
            else 0.0
        )
        reliable_baseline = (
            meaningful_history
            and historical_span_days >= FORGOTTEN_MIN_BASELINE_SPAN_DAYS
            and excluded_ambiguous_count == 0
        )

        if excluded_ambiguous_count:
            evidence_status: ForgottenContactEvidenceStatus = "ambiguous_direction"
        elif not meaningful_history:
            evidence_status = "insufficient_history"
        elif not reliable_baseline:
            evidence_status = "insufficient_baseline"
        else:
            evidence_status = "reliable_baseline"

        historical_monthly_baseline = None
        activity_decline_percentage = None
        ranking_score = None
        recent_monthly_activity = (
            recent_count
            / FORGOTTEN_RECENT_WINDOW_DAYS
            * FORGOTTEN_RECENT_MONTH_DAYS
        )
        if reliable_baseline and historical_span_days > 0:
            historical_monthly_baseline = (
                historical_count
                / historical_span_days
                * FORGOTTEN_RECENT_MONTH_DAYS
            )
            if historical_monthly_baseline > 0:
                decline_fraction = max(
                    0.0,
                    min(
                        1.0,
                        1.0
                        - recent_monthly_activity / historical_monthly_baseline,
                    ),
                )
                activity_decline_percentage = decline_fraction * 100
                if days_since_last is not None:
                    historical_evidence = min(
                        1.0,
                        historical_count / FORGOTTEN_EVIDENCE_MESSAGE_CAP,
                    )
                    inactivity_factor = min(
                        1.0,
                        days_since_last / FORGOTTEN_SCORE_INACTIVITY_CAP_DAYS,
                    )
                    ranking_score = round(
                        100
                        * historical_evidence
                        * (
                            FORGOTTEN_SCORE_INACTIVITY_WEIGHT * inactivity_factor
                            + FORGOTTEN_SCORE_DECLINE_WEIGHT * decline_fraction
                        ),
                        2,
                    )

        if evidence_status != "reliable_baseline" or days_since_last is None:
            classification = "insufficient_data"
        elif days_since_last >= FORGOTTEN_INACTIVE_DAYS:
            classification = "inactive"
        elif (
            activity_decline_percentage is not None
            and activity_decline_percentage
            >= FORGOTTEN_DECLINE_THRESHOLD * 100
        ):
            classification = "activity_declined"
        else:
            classification = "active"

        (
            source_account_ids,
            source_contact_ids,
            source_account_labels,
            platforms,
            platform_user_ids,
            identity_ids,
        ) = source_ids[group_key]
        contacts.append(
            ForgottenContact(
                account_id=(
                    min(source_account_ids)
                    if len(source_account_ids) == 1
                    else None
                ),
                contact_id=row.contact_id,
                canonical_identity_id=min(identity_ids) if identity_ids else None,
                identity_group_id=row.identity_group_id,
                platforms=sorted(platforms),
                source_account_ids=sorted(source_account_ids),
                source_account_labels=sorted(source_account_labels),
                source_contact_ids=sorted(source_contact_ids),
                platform_user_ids=sorted(platform_user_ids),
                display_name=row.display_name,
                interaction_chat_count=int(row.interaction_chat_count),
                first_message_at=first_message_at,
                last_message_at=last_message_at,
                days_since_last_communication=days_since_last,
                owner_message_count=owner_message_count,
                contact_message_count=contact_message_count,
                total_message_count=owner_message_count + contact_message_count,
                excluded_ambiguous_message_count=excluded_ambiguous_count,
                owner_text_length=owner_text_length,
                contact_text_length=contact_text_length,
                total_text_length=owner_text_length + contact_text_length,
                distinct_active_days=int(row.distinct_active_days),
                historical_message_count=historical_count,
                historical_active_days=int(row.historical_active_days),
                historical_active_month_count=historical_active_month_count,
                historical_activity_by_month=historical_months,
                recent_activity_by_month=recent_months,
                recent_owner_message_count=recent_owner_count,
                recent_contact_message_count=recent_contact_count,
                recent_message_count=recent_count,
                historical_monthly_baseline=(
                    round(historical_monthly_baseline, 2)
                    if historical_monthly_baseline is not None
                    else None
                ),
                recent_monthly_activity=round(recent_monthly_activity, 2),
                activity_decline_percentage=(
                    round(activity_decline_percentage, 2)
                    if activity_decline_percentage is not None
                    else None
                ),
                classification=classification,
                evidence_status=evidence_status,
                ranking_score=ranking_score,
            )
        )

    if sort_by == "display_name":
        reliable = [
            contact
            for contact in contacts
            if contact.classification != "insufficient_data"
        ]
        insufficient = [
            contact
            for contact in contacts
            if contact.classification == "insufficient_data"
        ]
        reliable.sort(
            key=lambda contact: contact.contact_id,
        )
        reliable.sort(
            key=lambda contact: (contact.display_name or "").casefold(),
            reverse=sort_direction == "desc",
        )
        insufficient.sort(
            key=lambda contact: contact.contact_id,
        )
        insufficient.sort(
            key=lambda contact: (contact.display_name or "").casefold(),
            reverse=sort_direction == "desc",
        )
        contacts = reliable + insufficient
    elif sort_by == "days_since_last_communication":
        sortable = [
            contact
            for contact in contacts
            if contact.days_since_last_communication is not None
        ]
        unsortable = [
            contact
            for contact in contacts
            if contact.days_since_last_communication is None
        ]
        sortable.sort(
            key=lambda contact: contact.contact_id,
        )
        sortable.sort(
            key=lambda contact: contact.days_since_last_communication or 0,
            reverse=sort_direction == "desc",
        )
        contacts = sortable + unsortable
    elif sort_by == "historical_message_count":
        contacts.sort(
            key=lambda contact: contact.contact_id,
        )
        contacts.sort(
            key=lambda contact: contact.historical_message_count,
            reverse=sort_direction == "desc",
        )
    else:
        sortable = [contact for contact in contacts if contact.ranking_score is not None]
        unsortable = [contact for contact in contacts if contact.ranking_score is None]
        sortable.sort(
            key=lambda contact: contact.contact_id,
        )
        sortable.sort(
            key=lambda contact: contact.ranking_score or 0.0,
            reverse=sort_direction == "desc",
        )
        contacts = sortable + unsortable

    options_contacts = contacts
    if platform:
        contacts = [
            contact for contact in contacts if platform in contact.platforms
        ]

    summary = ForgottenContactsSummary(
        source_account_count=source_account_count,
        eligible_contacts=len(contacts),
        meaningful_historical_contacts=sum(
            contact.historical_message_count >= FORGOTTEN_MIN_HISTORICAL_MESSAGES
            and contact.historical_active_days
            >= FORGOTTEN_MIN_HISTORICAL_ACTIVE_DAYS
            and contact.historical_active_month_count
            >= FORGOTTEN_MIN_HISTORICAL_ACTIVE_MONTHS
            for contact in contacts
        ),
        currently_inactive_contacts=sum(
            contact.days_since_last_communication is not None
            and contact.days_since_last_communication >= FORGOTTEN_INACTIVE_DAYS
            for contact in contacts
        ),
        declining_activity_contacts=sum(
            contact.activity_decline_percentage is not None
            and contact.activity_decline_percentage
            >= FORGOTTEN_DECLINE_THRESHOLD * 100
            for contact in contacts
        ),
        insufficient_data_contacts=sum(
            contact.classification == "insufficient_data" for contact in contacts
        ),
    )
    return ForgottenContactsStatistics(
        summary=summary,
        contacts=contacts[offset : offset + limit],
        pagination=PaginationMetadata(
            page=offset // limit + 1,
            page_size=limit,
            total=len(contacts),
        ),
        options=[
            SearchOption(
                value=str(index),
                label=contact.display_name or "Unnamed contact",
                platforms=contact.platforms,
                search_terms=[
                    *contact.platform_user_ids,
                    *contact.source_account_labels,
                ],
            )
            for index, contact in enumerate(options_contacts)
        ],
    )


@router.get(
    "/forgotten-contacts",
    response_model=ForgottenContactsStatistics,
    summary="Rank private contacts or group participants by activity",
    description=(
        "Uses only ordinary messages with a known owner alias and a matching "
        "canonical contact identity. The private scope includes 'personal_chat' "
        "chats with exactly one non-owner sender ID. The group scope includes "
        "all non-one-to-one chats and aggregates each participant across those "
        "chats. Owner IDs across every imported source "
        "account are treated as aliases and override source-local outgoing "
        "flags. Contact sender ID and is_outgoing must agree; contacts "
        "with any ambiguous ordinary-message direction are returned without a "
        "score. The recent window is the trailing "
        "90 days ending at request time. Historical evidence requires at least "
        "20 known-direction messages, five active UTC days, and three active "
        "pre-window months; a score additionally requires a 90-day historical "
        "span and no ambiguous messages. Monthly activity splits each UTC "
        "calendar month at the exact 90-day cutoff, so partial months are not "
        "compared as if complete. The baseline is historical messages per "
        "30 days across the dated pre-window activity span. Decline is "
        "max(0, 1 - recent monthly rate / historical monthly rate), capped at "
        "100%; 50% is the decline threshold. Score is 100 times min(historical "
        "messages / 100, 1) times (0.60 * min(days inactive / 180, 1) + "
        "0.40 * decline fraction). These descriptive thresholds are "
        "heuristics, not judgments about relationships. The optional platform "
        "filter limits result contacts and pagination to identities associated "
        "with that platform."
    ),
)
def get_forgotten_contacts(
    db: Session = Depends(get_db),
    scope: Literal["private", "group"] = Query(default="private"),
    sort_by: Literal[
        "ranking_score",
        "display_name",
        "days_since_last_communication",
        "historical_message_count",
    ] = Query(default="ranking_score"),
    sort_direction: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=FORGOTTEN_MAX_LIMIT)] = (
        DEFAULT_PAGE_SIZE
    ),
    platform: str | None = None,
) -> ForgottenContactsStatistics:
    return build_forgotten_contacts_statistics(
        db,
        scope=scope,
        sort_by=sort_by,
        sort_direction=sort_direction,
        limit=page_size,
        offset=(page - 1) * page_size,
        platform=platform,
    )
