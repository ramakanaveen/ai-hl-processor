# Headline Event Handling Approach

This note captures the intended behavior for:

- Live Feed
- History
- Duplicate suppression
- Relevant-history context during analysis
- Corrected results as source of truth


## Core Principle

UI presentation concerns and analysis-time reasoning concerns should be separate.

- `Live Feed` is a short-lived review surface for newly arrived events.
- `History` is the canonical audit log of analyzed items.
- Duplicate detection is an ingestion/analyzer concern, not a UI concern.
- Relevant historical context is a prompt-building concern, not a UI concern.


## Source Of Truth

Corrected results must be canonical everywhere.

If a user edits:

- headline: `Australian central bank holds rates as inflation eases`
- original model result: `AUD 90%`
- corrected result: `AUD 70%`

then the corrected version is the source of truth for:

- history rendering
- future duplicate checks
- prompt context when similar or identical headlines appear later
- Redis cache / timeline if used

The original model output may still be kept in audit logs if needed, but the system should treat the corrected version as authoritative.


## Live Feed

`Live Feed` should be timestamp-based.

It should show items that arrived within a configurable review window:

- `live_review_window_minutes`

Example:

- If the review window is 2 minutes, only headlines received in the last 2 minutes should appear in `Live Feed`.

Important:

- `Live Feed` should not remove or alter `History`.
- `Live Feed` is not a second copy of history.
- It is a temporary operator review surface.

Recommended UI behavior:

- Show reasoning expanded by default.
- Keep correction actions available.
- Expire items from live feed when they age out of the review window.


## History

`History` should remain stable and canonical.

It should not be hidden or filtered out just because the same headline is currently visible in `Live Feed`.

Recommended behavior:

- Always show historical items in newest-first order.
- If a headline is also currently active in live feed, show a small `Live` badge in history instead of hiding it.
- If a result was user-corrected, show:
  - `Edited` badge
  - last modified timestamp
  - optional editor identity

Important:

- Live feed visibility must never make history appear empty.
- UI overlap is better handled with labeling than removal.


## Exact Duplicate Handling

Exact duplicate handling should be configurable and should happen before the model call.

Recommended config:

- `ignore_duplicate_headlines`: boolean
- `duplicate_window_minutes`: integer

Definition:

- Two headlines are duplicates if their normalized text matches.
- Normalization can be simple:
  - trim whitespace
  - lowercase
  - optionally collapse repeated spaces

Example:

- At `T0`, headline arrives:
  - `Australian central bank holds rates as inflation eases`
- It is analyzed and later corrected to `AUD 70%`
- At `T0 + 15m`, the exact same normalized headline arrives again

If:

- `ignore_duplicate_headlines = true`
- `duplicate_window_minutes = 15`

then:

- do not call the model again
- do not create a new live item
- do not create a second canonical history item
- optionally log the duplicate suppression event for audit/metrics

If duplicate ignoring is disabled:

- the system may still process the item
- but it should consult the corrected canonical result as strong prior context


## Similar / Relevant Headline Handling

Not all related headlines are duplicates.

Example:

- Existing headline:
  - `Australian central bank holds rates as inflation eases`
- New headline:
  - `Australian central bank meeting increased interest rate`

These are not exact duplicates, so they should be analyzed again.

However, the new analysis should use recent relevant context.

Recommended config:

- `relevant_group_window_minutes`

This window controls how far back the system should look for relevant recent events when enriching the prompt.


## Analysis-Time Context Strategy

When a new headline arrives, the system should follow this order:

1. Normalize the incoming headline.
2. Check for exact duplicate within `duplicate_window_minutes`.
3. If duplicate suppression is enabled and a duplicate exists:
   - skip model call
   - optionally emit a duplicate-suppressed metric/log
4. If not an ignored duplicate:
   - gather relevant context
   - call the model
   - store the result canonically

Relevant context should include:

- exact prior corrected result for the same headline, if it exists
- similar historical headlines from file memory
- recent active currency impacts from Redis or equivalent recent-impact store
- recent corrected canonical items within `relevant_group_window_minutes`


## Currency-Relevance Behavior

For a new headline, the system does not know impacted currencies until after analysis.

So there are two reasonable approaches:

### Option A: Pre-analysis context using text similarity / topic matching

Before the model call, gather:

- similar headlines by keyword similarity
- same-country / same-central-bank / same-topic items
- recent exact or near-exact theme matches

This is the safest default and matches the current architecture best.

### Option B: Post-analysis enrichment using impacted currencies

After an initial analysis identifies likely impacted currencies such as `AUD`, gather recent `AUD` events from the relevant window and optionally:

- re-rank
- re-score
- re-run prompt with stronger context

This is more expensive and more complex.

Recommendation:

- Start with Option A for prompt enrichment before the model call.
- Use recent Redis impact graph and text-similar history as the main context source.
- Only add a second-pass re-analysis if there is a demonstrated need.


## Recommended Config Set

Suggested config values:

- `live_review_window_minutes = 2`
- `ignore_duplicate_headlines = true`
- `duplicate_window_minutes = 15`
- `relevant_group_window_minutes = 60`

Meaning:

- headlines remain in live feed for 2 minutes
- exact duplicate headlines within 15 minutes are ignored
- prompt context can include relevant items from the last 60 minutes


## Recommended UI Behavior

### Live Feed

- show only fresh items within `live_review_window_minutes`
- reasoning expanded by default
- corrections available
- no dependency on whether the same item exists in history

### History

- always show canonical stored results
- never hide items because they are active in live feed
- show badges such as:
  - `Edited`
  - `Live`
- show last modified time if corrected


## Recommended Backend Behavior

### On headline ingest

1. normalize headline
2. check duplicate policy
3. if suppressed:
   - log and stop
4. else:
   - gather relevant context
   - call agent
   - persist canonical result
   - emit live event

### On correction

1. update canonical stored result
2. update Redis cache / active graph if applicable
3. retain separate correction audit entry if needed
4. ensure future analysis reads corrected canonical state


## Anti-Patterns To Avoid

- Hiding history items just because they are currently live
- Treating UI overlap logic as duplicate suppression
- Reusing uncorrected model output after a user has corrected the result
- Performing duplicate checks only in the UI
- Letting live-feed expiration affect canonical storage


## Practical Next Steps

Recommended implementation order:

1. Remove history-hiding behavior and replace it with a `Live` badge.
2. Add backend config for:
   - `ignore_duplicate_headlines`
   - `duplicate_window_minutes`
   - `relevant_group_window_minutes`
3. Add duplicate suppression before agent invocation.
4. Ensure prompt-building uses corrected canonical history and recent relevant items.
5. Add logs/metrics for:
   - duplicate suppressed
   - correction applied
   - relevant context items included in prompt

