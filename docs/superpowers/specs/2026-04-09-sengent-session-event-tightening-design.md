# Sengent Session Event Tightening Design

## Context

`Sengent` already records useful session facts, but the runtime contract is
split across several structures:

- `SupportSessionState` stores active task, anchor query, and clarification
  slots
- `SessionTurnResult` stores adversarial / pilot replay trace
- `FeedbackTurnSnapshot` stores runtime feedback capture
- pilot readiness and closed-loop reports derive their own failure payloads

This is enough to run the current system, but not enough to make session
history a stable runtime primitive. The same turn is currently represented in
different shapes depending on whether it came from:

- interactive CLI chat
- adversarial session replay
- pilot readiness replay
- runtime feedback capture

That makes the system harder to reason about, and it weakens both of the
consumers we care about:

- human support trace / troubleshooting review
- eval / replay / baseline / closed-loop analysis

## Problem Statement

The current system does not lack data. It lacks a unified event contract.

### Drift 1: Session State And Session Trace Are Separate Worlds

`SupportSessionState` is the live state machine, but the runtime does not keep
an equally first-class structured log of the turns that produced that state.
The system can answer a question like "what is the current active task?" more
easily than it can answer:

- why did the system reuse the anchor on turn 2?
- what facts were active when the final reply was generated?
- which sources and resolver path produced the answer?

### Drift 2: Replay And Feedback Use Private Snapshots

`SessionTurnResult` and `FeedbackTurnSnapshot` carry overlapping fields:

- `prompt`
- `effective_query`
- `task`
- `issue_type`
- `route_reason`
- `parsed_intent`
- `response_mode`
- `reused_anchor`

But they are not the same type, and neither one is clearly the runtime source
of truth.

### Drift 3: Runtime Feedback Stores Copies, Not References

`runtime/feedback/runtime_feedback.jsonl` currently stores copied turn payloads
under `captured_turns`. This is acceptable for the MVP, but it creates two
problems:

- runtime feedback records can drift from the session representation that
  replay uses
- there is no durable session id / turn id contract to join feedback back to
  the original runtime trace

### Drift 4: Eval Reports Consume Derived Views, Not Stable Events

`pilot_readiness.py` and `pilot_closed_loop.py` consume replay results and
feedback payloads, but they do not read from a single stable event-backed
representation. This increases the chance that:

- a new field must be added in 3 places
- replay and runtime feedback diverge subtly
- debugging a regression requires reading several partially redundant objects

## Design Goal

Introduce a unified session / event runtime contract for `Sengent` without
changing the product direction.

This is a runtime-structure tightening pass, not a platformization effort.

It must:

- stay inside the current local CLI architecture
- preserve rule-first routing and structured knowledge packs
- improve both human trace review and eval / closed-loop replay
- keep `runtime/` as local, non-git-tracked operational data

It must not:

- introduce managed-agent infrastructure
- replace local session state with distributed orchestration
- switch to RAG-first retrieval
- make LLM output the primary route owner

## Target Runtime Model

### 1. `SupportSessionRecord`

Represents one local support session.

Owns:

- `session_id`
- `schema_version`
- `created_at`
- `repo_root`
- `git_sha`
- `source_directory`
- `knowledge_directory`
- optional `mode` such as `interactive` or `replay`

This is the durable session identity that runtime feedback and replay can
reference.

### 2. `SupportTurnEvent`

Represents one completed support turn.

Required fields:

- `event_type = "turn_resolved"`
- `session_id`
- `turn_id`
- `turn_index`
- `timestamp`
- `raw_query`
- `effective_query`
- `reused_anchor`
- `task`
- `issue_type`
- `route_reason`
- `parsed_intent.intent`
- `parsed_intent.module`
- `response_mode`
- `response_text`
- `state_before`
- `state_after`

Recommended fields:

- `confirmed_facts`
- `open_clarification_slots`
- `sources`
- `boundary_tags`
- `resolver_path`

This becomes the single durable fact record for replay, feedback, and human
trace review.

### 3. `SupportTurnView`

A small derived view used by existing evaluation logic.

It keeps the shape currently expected by replay / pilot code:

- prompt
- effective query
- reused anchor
- response
- task
- issue type
- route reason
- parsed intent
- response mode

But this view is derived from `SupportTurnEvent`, not stored separately as an
independent source of truth.

### 4. `FeedbackRecord`

Feedback should reference unified session events instead of carrying a private
snapshot schema.

Required fields:

- `record_id`
- `submitted_at`
- `source`
- `scope`
- `session_id`
- `selected_turn_ids`
- `summary`
- `expected_answer`
- `expected_mode`
- `expected_task`
- `scorable`
- `git_sha`

Optional denormalized fields are allowed for convenience, but the canonical
turn payload comes from the session event log.

## Event Types

This tightening pass should use a deliberately small event vocabulary.

### `session_started`

Emitted when a session is created.

Purpose:

- establish durable session identity
- store runtime metadata once

### `turn_resolved`

Emitted once per completed support turn.

Purpose:

- record planner decision, resolved answer, and state transition together
- become the durable input for replay, feedback, and human review

### `feedback_recorded`

Emitted when runtime feedback is submitted.

Purpose:

- bind user feedback to a known session and concrete turn ids
- keep feedback traceable without defining a second turn schema

No token-stream or fine-grained planner micro-events are needed in this pass.
That would add noise before the current system needs it.

## Runtime Layout

Add these runtime files:

- `runtime/sessions/index.jsonl`
- `runtime/sessions/<session_id>.jsonl`
- `runtime/feedback/runtime_feedback.jsonl`

Rules:

- `index.jsonl` stores one summary record per session
- `<session_id>.jsonl` stores ordered session events
- feedback records reference `session_id` and `turn_id`
- runtime files remain local and must not be committed

## Responsibility Boundaries

### `cli.py`

Owns:

- creating or resuming the live session record
- writing runtime session events during interactive chat
- selecting which turn ids are included in `/feedback` and `/feedback session`

Must not own:

- bucketing logic
- replay scoring logic
- event schema migration logic

### `support_state.py`

Owns:

- live state dataclass used during a session
- lightweight serialization helpers for `state_before` and `state_after`

Must not own:

- event logging
- eval-specific fields

### `adversarial_sessions.py`

Owns:

- replay execution against the current support runtime
- conversion from durable turn events into `SupportTurnView`

Must not own:

- a competing turn schema

### `feedback_runtime.py`

Owns:

- feedback normalization
- feedback record construction
- feedback file append / load helpers

Must not own:

- its own private per-turn snapshot schema

### `pilot_readiness.py` and `pilot_closed_loop.py`

Own:

- evaluation cases
- bucketing
- scorecards
- recommendations

Must not own:

- alternate turn trace representations
- ad hoc runtime feedback payload reconstruction

## Migration Strategy

This pass should directly unify the architecture rather than keep a long-lived
dual schema.

### Step 1

Introduce a dedicated runtime module for:

- session records
- turn events
- event log IO
- derived turn views

### Step 2

Teach the CLI to open a runtime session and append:

- `session_started`
- `turn_resolved`
- `feedback_recorded`

### Step 3

Replace `SessionTurnResult` and `FeedbackTurnSnapshot` with unified event-backed
views.

### Step 4

Update pilot readiness and closed-loop replay to consume the unified turn view.

### Step 5

Update runtime feedback replay to resolve selected turns from session event
logs instead of replaying copied snapshots.

## JSON Contract Notes

The runtime log should prefer explicit nested objects over flattened ad hoc
field groups.

Recommended shape inside `turn_resolved`:

- `planner`
  - `raw_query`
  - `effective_query`
  - `reused_anchor`
  - `task`
  - `issue_type`
  - `route_reason`
  - `parsed_intent`
- `answer`
  - `response_mode`
  - `response_text`
  - `sources`
  - `boundary_tags`
  - `resolver_path`
- `state_before`
- `state_after`

This keeps the contract readable while still allowing a simple derived view for
existing eval code.

## Validation

This pass needs new regression coverage for:

- event log creation for interactive sessions
- turn event serialization and reload
- feedback submission referencing session / turn ids
- replay conversion from event log to eval view
- pilot closed-loop loading runtime feedback through event references

And it must preserve:

- `pytest`
- `pilot_readiness_eval.py`
- `pilot_closed_loop.py`

## Non-Goals

This pass does not do:

- cloud session storage
- multi-agent orchestration
- memory retrieval service
- token-level telemetry
- event schema version negotiation across machines
- customer-facing UI redesign

## Success Criteria

This tightening pass succeeds if:

1. one support turn has one canonical runtime representation
2. runtime feedback references sessions and turns instead of carrying a private
   turn schema
3. pilot replay and closed-loop scoring consume the same derived turn view
4. human runtime trace and eval replay can both read the same session log
5. all current gates stay green without weakening the rule-first architecture
