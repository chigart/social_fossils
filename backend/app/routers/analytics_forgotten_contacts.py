from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import TelegramAccount
from app.schemas.analytics import (
    ForgottenContact,
    ForgottenContactEvidenceStatus,
    ForgottenContactMonthlyActivity,
    ForgottenContactsStatistics,
    ForgottenContactsSummary,
)

from .analytics_forgotten_queries import (
    build_forgotten_contact_queries,
)

from .analytics_constants import (
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
    sort_by: Literal[
        "ranking_score",
        "display_name",
        "days_since_last_communication",
        "historical_message_count",
    ] = "ranking_score",
    limit: int = 100,
    as_of: datetime | None = None,
) -> ForgottenContactsStatistics:
    if not 1 <= limit <= FORGOTTEN_MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {FORGOTTEN_MAX_LIMIT}.")

    source_account_count = int(db.scalar(select(func.count(TelegramAccount.id))) or 0)
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
        )

    current_time = _as_utc(as_of or datetime.now(timezone.utc))
    recent_start = current_time - timedelta(days=FORGOTTEN_RECENT_WINDOW_DAYS)
    owner_ids = select(TelegramAccount.telegram_user_id).where(
        TelegramAccount.telegram_user_id.is_not(None)
    )

    eligible_pairs, aggregate_statement, monthly_statement = (
        build_forgotten_contact_queries(
            db,
            owner_ids,
            recent_start,
            current_time,
        )
    )

    monthly_by_contact: dict[
        tuple[int, int | None], list[dict[str, int | str]]
    ] = {}
    for month_row in db.execute(monthly_statement):
        monthly_by_contact.setdefault(
            (month_row.identity_group_id, month_row.identity_source_account_id), []
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
            eligible_pairs.c.identity_source_account_id,
            eligible_pairs.c.account_id,
            eligible_pairs.c.contact_id,
            TelegramAccount.username.label("account_username"),
            TelegramAccount.name.label("account_name"),
        ).distinct()
        .join(TelegramAccount, TelegramAccount.id == eligible_pairs.c.account_id)
    )
    source_ids: dict[
        tuple[int, int | None], tuple[set[int], set[int], set[str]]
    ] = {}
    for source_row in source_rows:
        key = (
            source_row.identity_group_id,
            source_row.identity_source_account_id,
        )
        accounts, contact_ids, account_labels = source_ids.setdefault(
            key, (set(), set(), set())
        )
        accounts.add(source_row.account_id)
        contact_ids.add(source_row.contact_id)
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
        group_key = (row.identity_group_id, row.identity_source_account_id)
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

        source_account_ids, source_contact_ids, source_account_labels = source_ids[
            group_key
        ]
        contacts.append(
            ForgottenContact(
                account_id=(
                    min(source_account_ids)
                    if len(source_account_ids) == 1
                    else None
                ),
                contact_id=row.contact_id,
                canonical_identity_id=row.canonical_identity_id,
                source_account_ids=sorted(source_account_ids),
                source_account_labels=sorted(source_account_labels),
                source_contact_ids=sorted(source_contact_ids),
                telegram_user_id=row.telegram_user_id,
                display_name=row.display_name,
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
        contacts.sort(
            key=lambda contact: (
                contact.classification == "insufficient_data",
                (contact.display_name or "").casefold(),
                contact.contact_id,
            )
        )
    elif sort_by == "days_since_last_communication":
        contacts.sort(
            key=lambda contact: (
                contact.days_since_last_communication is None,
                -(contact.days_since_last_communication or 0),
                contact.contact_id,
            )
        )
    elif sort_by == "historical_message_count":
        contacts.sort(
            key=lambda contact: (
                -contact.historical_message_count,
                contact.contact_id,
            )
        )
    else:
        contacts.sort(
            key=lambda contact: (
                contact.ranking_score is None,
                -(contact.ranking_score or 0.0),
                contact.contact_id,
            )
        )

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
        contacts=contacts[:limit],
    )


@router.get(
    "/forgotten-contacts",
    response_model=ForgottenContactsStatistics,
    summary="Rank private contacts by inactivity and declining communication",
    description=(
        "Uses only ordinary messages in 'personal_chat' chats with a known "
        "owner alias, exactly one non-owner sender ID, and a matching "
        "canonical contact identity. Owner IDs across every imported source "
        "account are treated as aliases and override source-local outgoing "
        "flags. Contact sender ID and is_outgoing must agree; contacts "
        "with any ambiguous ordinary-message direction are returned without a "
        "score. Group chats are excluded. The recent window is the trailing "
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
        "heuristics, not judgments about relationships."
    ),
)
def get_forgotten_contacts(
    db: Session = Depends(get_db),
    sort_by: Literal[
        "ranking_score",
        "display_name",
        "days_since_last_communication",
        "historical_message_count",
    ] = Query(default="ranking_score"),
    limit: int = Query(default=100, ge=1, le=FORGOTTEN_MAX_LIMIT),
) -> ForgottenContactsStatistics:
    return build_forgotten_contacts_statistics(
        db,
        sort_by=sort_by,
        limit=limit,
    )
