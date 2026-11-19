# Analytics logic

## Cache lookup and invalidation

```mermaid
flowchart TD
    Request["Incoming request"]
    Eligible{"GET under /api/analytics/<br/>or GET /api/identity-links?"}
    Route["Run route without cache"]
    Key["Key by request path<br/>and ordered query parameters"]
    Revision["Read analytics revision"]
    Hit{"Response stored<br/>for key and revision?"}
    Cached["Return cached JSON"]
    Query["Run route query"]
    Success{"HTTP status is 200?"}
    Fresh{"Revision unchanged<br/>after query?"}
    Store["Upsert response body"]
    Return["Return route response"]

    Request --> Eligible
    Eligible -->|"No"| Route
    Route --> Return
    Eligible -->|"Yes"| Key --> Revision --> Hit
    Hit -->|"Yes"| Cached
    Hit -->|"No"| Query --> Success
    Success -->|"No"| Return
    Success -->|"Yes"| Fresh
    Fresh -->|"Yes"| Store --> Return
    Fresh -->|"No"| Return
```

The revision combines the analytics cache version with import-session count,
maximum ID and latest finish time, plus identity-link-event count and maximum
ID. Completed imports and identity-link actions therefore make affected cache
keys miss without deleting old entries. A request result is stored only when
its revision is still current. Time-dependent analytics remain cached until
the revision changes.

## Direct-message friendship status

```mermaid
flowchart TD
    Input["Personal-chat ordinary messages"]
    Resolve["Resolve peer identity<br/>combine explicitly linked identities"]
    Unique{"Exactly one non-owner<br/>peer in the chat?"}
    Ignore["Exclude ambiguous chat"]
    Count["Count dated, non-empty text messages<br/>in UTC windows and years"]
    Active{"At least 20 text messages<br/>in last 6 months and owner sent<br/>a message in that window?"}
    Annual{"At least 200 exchanged<br/>text messages in a complete UTC year<br/>and owner sent at least one?"}
    Continuous{"Has owner sent a text message<br/>in every year since a qualifying year,<br/>and owner activity is within 12 months?"}
    Historical{"Any qualifying close year?"}
    Output["Return Active, Close,<br/>and/or exClose labels"]
    NoLabel["No friendship status"]

    Input --> Resolve --> Unique
    Unique -->|"No"| Ignore
    Unique -->|"Yes"| Count
    Count --> Active
    Count --> Annual --> Continuous
    Continuous -->|"Yes"| Output
    Continuous -->|"No"| Historical
    Active -->|"Yes"| Output
    Active -->|"No"| Historical
    Historical -->|"Yes"| Output
    Historical -->|"No"| NoLabel
```

Active and Close may both apply. A contact with historical Close evidence but
not current Close status is exClose. The close-friends yearly timeline uses
complete UTC years; when the latest year is partial, it repeats the previous
year's count.

## Communication balance

```mermaid
flowchart TD
    Candidate["One-to-one personal chat"]
    Eligible{"Owner known and exactly one<br/>non-owner sender resolves<br/>to an identity?"}
    Exclude["Exclude group or ambiguous chat"]
    Volume["Combine explicitly linked identities;<br/>count ordinary text volume"]
    Minimum{"At least 500 total<br/>text characters?"}
    Insufficient["insufficient_data"]
    Share["Compute owner's share<br/>of total text length"]
    StrongOwner{"Owner share >= 80%?"}
    StrongContact{"Owner share <= 20%?"}
    Balanced{"Owner share is 40%-60%?"}
    MostlyOwner["mostly_owner"]
    MostlyContact["mostly_contact"]
    StronglyOwner["strongly_owner"]
    StronglyContact["strongly_contact"]
    BalancedOut["balanced"]

    Candidate --> Eligible
    Eligible -->|"No"| Exclude
    Eligible -->|"Yes"| Volume --> Minimum
    Minimum -->|"No"| Insufficient
    Minimum -->|"Yes"| Share --> StrongOwner
    StrongOwner -->|"Yes"| StronglyOwner
    StrongOwner -->|"No"| StrongContact
    StrongContact -->|"Yes"| StronglyContact
    StrongContact -->|"No"| Balanced
    Balanced -->|"Yes"| BalancedOut
    Balanced -->|"No, above 60%"| MostlyOwner
    Balanced -->|"No, below 40%"| MostlyContact
```

These are descriptive heuristics, not scientifically validated relationship
measurements. Text length is based on stored text content, not bytes or media.

## Forgotten contacts

```mermaid
flowchart TD
    Messages["Aggregate ordinary interactions<br/>for selected private/group scope"]
    Identity["Combine explicitly linked identities;<br/>separate ambiguous direction"]
    History{"At least 20 historical messages,<br/>5 active days, and 3 active months?"}
    Span{"Historical span at least 90 days<br/>and no ambiguous messages?"}
    Insufficient["insufficient_data"]
    Baseline["Compare historical monthly baseline<br/>with recent 90-day activity"]
    Last{"Days since last communication<br/>at least 90?"}
    Inactive["inactive"]
    Decline{"Activity declined<br/>by at least 50%?"}
    Declined["activity_declined"]
    Active["active"]
    Score["For reliable history, rank with capped<br/>historical evidence, inactivity (60%),<br/>and decline (40%)"]

    Messages --> Identity --> History
    History -->|"No"| Insufficient
    History -->|"Yes"| Span
    Span -->|"No"| Insufficient
    Span -->|"Yes"| Baseline --> Last
    Last -->|"Yes"| Inactive
    Last -->|"No"| Decline
    Decline -->|"Yes"| Declined
    Decline -->|"No"| Active
    Inactive --> Score
    Declined --> Score
    Active --> Score
```

The analysis requires a meaningful historical baseline before assigning an
activity classification. Its score is an ordering aid, not a probability.

## Group interactions

```mermaid
flowchart TD
    Scope["Select group interactions<br/>or a target participant"]
    Target{"Target participant selected?"}
    Resolve["Resolve target contact and<br/>explicit identity group"]
    Chats["Select non-personal chats<br/>with known owner account"]
    Messages["Keep ordinary messages<br/>whose platform matches the chat"]
    Limit["For target analysis, include the target's<br/>group chats and owner messages there"]
    Preaggregate["Preaggregate by chat, platform,<br/>sender, direction, UTC day,<br/>and historical/recent period"]
    Direction["Identify owner and contact senders;<br/>exclude unknown direction from<br/>direction-specific measures"]
    Aggregate["Aggregate messages, text length,<br/>active days, date ranges, and<br/>monthly/recent measures"]
    Result["Return participant interaction statistics"]

    Scope --> Target
    Target -->|"Yes"| Resolve --> Chats
    Target -->|"No"| Chats
    Chats --> Messages --> Limit --> Preaggregate --> Direction --> Aggregate --> Result
```

Group analysis works from ordinary messages and daily preaggregation. When a
specific participant is requested, explicitly linked identities are resolved
and the query includes owner activity in the target's eligible group chats.
