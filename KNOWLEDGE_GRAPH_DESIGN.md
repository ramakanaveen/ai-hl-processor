# Knowledge Graph And Fast/Slow Loop Design

This document describes a staged design for:

- Phase 1: current fast impact engine as the initial user-facing solution
- deduplication behavior between live feed and history
- a future fast/slow loop architecture
- a knowledge graph / knowledge base for relevant-context retrieval


## Priority Order

Current implementation priority should be:

1. Preserve the existing fast impact path so the product remains usable.
2. Fix live feed / history deduplication at the UI level.
3. Design and build the slow loop that produces structured knowledge.
4. Use that structured knowledge to improve the fast loop.

That means the graph is important, but it should not block the initial working solution.


## Phase 1 Goal

Phase 1 should keep the current user-visible behavior mostly intact:

- a headline arrives
- the system performs a quick impact assessment
- the result is shown to the user quickly
- users can correct the result
- corrected results become canonical

The current impact engine can be treated as:

- `Thread 1`
- `Phase 1 fast loop`
- initial low-latency path

This path should remain the initial production-facing solution while the slower graph-building architecture is introduced in parallel.


## Near-Term UI Requirement

The immediate UI requirement is deduplication between `Live Feed` and `History`.

Recommended near-term behavior:

- `Live Feed` remains a timestamp-based review surface.
- `History` remains canonical and stable.
- history items should not disappear because they are live
- if the same headline is active in live feed, history should show a `Live` badge instead of hiding it

This is a UI concern only.

It should not be confused with:

- duplicate headline suppression
- analysis-time relevance retrieval
- graph search


## Two-Speed Architecture

The target architecture should have two loops.

### Thread 1: Fast Loop

Purpose:

- low-latency impact prediction
- produce a result quickly enough for live operator review

Characteristics:

- should return quickly
- should use a bounded amount of context
- should not depend on expensive graph reasoning
- should use corrected canonical history when available

Inputs:

- incoming headline
- exact duplicate signal
- top relevant context retrieved from knowledge base / graph
- recent active market signals

Output:

- impacted currencies / entities
- confidence
- reasoning
- metadata about evidence used


### Thread 2: Slow Loop

Purpose:

- perform deeper semantic enrichment
- normalize actors, themes, and relationships
- write knowledge into a structured store
- improve future fast-loop retrieval quality

Characteristics:

- can be asynchronous
- can take longer than the fast loop
- can enrich the same headline after the first user-visible result is already available
- should update the knowledge base, not necessarily the user-facing impact immediately

Inputs:

- incoming headline
- fast-loop result
- user corrections if available later
- historical context

Output:

- normalized entities
- normalized themes
- graph nodes and edges
- richer event-family classification
- stronger relevance signals for future incoming headlines


## Why The Split Is Correct

This problem has two conflicting needs:

- users need a quick answer now
- the system needs richer semantic structure to improve future answers

If both are forced into one path, the system becomes:

- too slow for live use
- too hard to evolve
- too tightly coupled to one prompt

The fast/slow split allows:

- quick operational response
- gradual knowledge accumulation
- improved future context retrieval


## Conceptual Data Flow

At `T0`, when a headline arrives:

1. Headline ingestion
2. Fast loop starts immediately
3. Slow loop starts in parallel
4. Fast-loop result is shown to user
5. Slow loop enriches and stores graph knowledge
6. User corrections, if any, update canonical result

At `T1`, when a new headline arrives:

1. Extract lightweight anchors from headline
2. Query knowledge base / graph using those anchors
3. Retrieve bounded relevant context
4. Run fast loop with headline + retrieved context
5. Run slow loop in parallel to enrich the new item


## Fast Loop Design

### Fast Loop Responsibility

The fast loop should answer:

- which currencies or entities are likely impacted right now

It should not try to solve the full semantic understanding problem.


### Fast Loop Inputs

The fast loop should use:

- current headline text
- corrected canonical record if the exact headline has been seen before
- recent related items from the knowledge base
- recent active impact graph items
- optional duplicate suppression result


### Fast Loop Bounded Context Rule

The fast loop should only use a bounded amount of context.

Suggested limits:

- top 3 to 5 relevant historical headlines
- top 3 recent active currency signals
- exact prior corrected result if it exists

This keeps latency predictable and prompts manageable.


### Fast Loop Phase 1

Phase 1 should keep the current analysis engine and improve it incrementally.

Recommended Phase 1 additions:

- corrected canonical history as source of truth
- duplicate suppression policy
- relevant-history retrieval via simple scoring
- recent active currency context from Redis or equivalent

This gives immediate product value without waiting for the full graph.


## Slow Loop Design

### Slow Loop Responsibility

The slow loop should answer:

- what family of event is this
- which actors and themes does it belong to
- what relationships should be written into the knowledge base


### Slow Loop Tasks

For each headline, the slow loop should attempt to derive:

- canonical actor(s)
- country / region
- event theme(s)
- event subtype(s)
- likely macro factors
- impacted currencies
- evidence relationships
- temporal relationships

Example:

Headline:

- `Australian central bank holds rates as inflation eases`

Possible slow-loop structured output:

- actor: `Reserve Bank of Australia`
- aliases: `RBA`, `Australian central bank`
- country: `Australia`
- theme: `monetary_policy`
- subtype: `rate_hold`
- macro factor: `inflation_easing`
- impacted currency: `AUD`


## Knowledge Graph Purpose

The graph should not exist for its own sake.

Its purpose is to support:

- better retrieval of relevant context for future headlines
- family-level grouping of related events
- richer understanding of how actors, themes, and currencies connect over time


## Recommended Graph Model

### Node Types

Suggested first-pass node types:

- `Headline`
- `Actor`
- `Country`
- `Theme`
- `Currency`
- `MacroFactor`
- optionally `EventFamily`


### Edge Types

Suggested first-pass edge types:

- `MENTIONS_ACTOR`
- `MENTIONS_COUNTRY`
- `HAS_THEME`
- `HAS_MACRO_FACTOR`
- `IMPACTS_CURRENCY`
- `BELONGS_TO_EVENT_FAMILY`
- `RELATED_TO`
- `CORRECTED_TO`
- `TEMPORALLY_NEAR`


### Edge Metadata

Each edge should support metadata such as:

- confidence
- created_at
- source
- corrected / canonical flag where relevant
- weight / score


## Event Family Concept

A very important abstraction is `EventFamily`.

This is how the system groups related headlines beyond exact text match.

Examples:

- `RBA monetary policy`
- `Fed rate decision`
- `China trade policy`
- `BoJ FX intervention`

Individual headlines should map into event families, and those families should become major retrieval anchors.


## Graph Search At T1

Graph search should be anchor-driven, not open-ended.

When a new headline arrives, the system should first extract a small set of anchors.

Suggested anchors:

- actor
- country
- theme
- macro factor
- optional likely impacted currencies

Then search should:

1. resolve the anchors to canonical nodes
2. expand locally from those nodes
3. rank nearby headline nodes and currency signals
4. return only the strongest context items


## What Should Be The Basis Of Search

The graph search basis should be:

1. actor/entity anchors
2. theme/event anchors
3. country/region anchors
4. corrected recent currency impacts as supporting signals
5. recency

The search should not rely on:

- raw keyword overlap alone
- impacted currency alone
- unrestricted graph traversal


## Relevance Scoring

At retrieval time, candidate relevant items should be scored.

A practical scoring model:

- same actor: very strong
- same theme: strong
- same country: medium
- same macro factor: medium
- same impacted currency: supporting
- corrected canonical item: bonus
- more recent item: higher score

Illustrative formula:

`relevance_score = actor_weight + theme_weight + country_weight + macro_weight + currency_weight + correction_bonus + recency_decay`

This does not need to be mathematically perfect at first.

It only needs to be:

- explicit
- inspectable
- tunable


## Duplicate Handling

Duplicate handling is separate from relevance.

### Exact Duplicate

If the normalized headline matches an existing canonical headline within a configured window:

- optionally suppress it
- do not call the model if suppression is enabled

Suggested config:

- `ignore_duplicate_headlines`
- `duplicate_window_minutes`

Example:

At `T0`:

- `Australian central bank holds rates as inflation eases`
- analyzed as `AUD 90%`
- corrected to `AUD 70%`

At `T0 + 15m`:

- the exact same normalized headline arrives again

If duplicate suppression is enabled:

- ignore it
- do not create a second live item
- do not create a second canonical history record
- use the corrected canonical record as the authoritative version


### Related But Not Duplicate

Example:

- old: `Australian central bank holds rates as inflation eases`
- new: `Australian central bank meeting increased interest rate`

This is not a duplicate.

Recommended behavior:

- run the fast loop
- use graph / knowledge-base retrieval to gather relevant context
- include recent relevant `AUD` / RBA / Australia items


## Suggested Configs

Suggested near-term configuration set:

- `live_review_window_minutes = 2`
- `ignore_duplicate_headlines = true`
- `duplicate_window_minutes = 15`
- `relevant_group_window_minutes = 60`
- `max_relevant_items_for_fast_loop = 5`


## Storage Strategy

The system does not need a full graph database on day one.

Recommended staged approach:

### Stage 1

Use current stores plus richer metadata:

- file store for canonical results
- Redis for duplicate checks and recent active impacts
- structured enrichment records written alongside canonical results

### Stage 2

Introduce graph-oriented storage or indexed structures:

- actor index
- theme index
- event-family index
- recent relevance index

### Stage 3

Move to a more formal graph representation if necessary:

- graph database
- document + edge index combination
- vector + structured hybrid retrieval


## Recommended Implementation Phases

### Phase 1

Ship the fast loop as the primary user-facing path.

Implement:

- corrected results as canonical
- stable history
- `Live` badge instead of hiding history entries
- duplicate suppression
- simple relevant retrieval using actor/theme/currency/time scoring


### Phase 2

Introduce slow-loop enrichment.

Implement:

- actor normalization
- theme normalization
- event family generation
- structured enrichment records


### Phase 3

Promote slow-loop output into a true knowledge base / graph.

Implement:

- graph nodes and edges
- anchor-driven retrieval
- ranked context selection for fast loop


## Recommended Immediate Next Steps

In order:

1. Fix the current UI dedup behavior so history is not hidden.
2. Add `Live` badges to history for currently active headlines.
3. Add backend duplicate suppression config and policy.
4. Add a simple relevance scorer before the fast-loop model call.
5. Design the slow-loop output schema.
6. Build the first graph/index representation from slow-loop output.


## Summary

The best architecture is:

- keep the current fast impact engine as Phase 1
- treat it as the first production path
- build a slower semantic enrichment path in parallel
- use the slow path to create a structured knowledge base
- use anchor-driven retrieval from that knowledge base to improve future fast-loop analysis

This keeps the system practical in the near term while building toward a much stronger long-term design.

