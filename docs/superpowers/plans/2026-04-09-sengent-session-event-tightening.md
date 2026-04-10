# Sengent Session Event Tightening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current split session trace / feedback snapshot model with one unified session-event runtime contract, persisted under `runtime/`, while preserving the current rule-first support flow and pilot closed-loop behavior.

**Architecture:** Add a dedicated runtime event module that owns session records, turn events, JSONL IO, and derived turn views. Make CLI chat write event logs, make runtime feedback reference session / turn ids, and make adversarial / pilot / closed-loop consumers read the unified derived turn view instead of private snapshot types.

**Tech Stack:** Python 3.11, pytest, dataclasses, local JSONL runtime logs, deterministic support coordinator and reference resolver

---

## File Map

- Add: `src/sentieon_assist/session_events.py`
  - Define `SupportSessionRecord`, `SupportTurnEvent`, `SupportTurnView`, event append / load helpers, and session metadata helpers.
- Modify: `src/sentieon_assist/support_state.py`
  - Add serialization helpers for state snapshots.
- Modify: `src/sentieon_assist/cli.py`
  - Create runtime session records, append `turn_resolved` events, and attach feedback submissions to session / turn ids.
- Modify: `src/sentieon_assist/adversarial_sessions.py`
  - Remove `SessionTurnResult` as the source of truth and derive replay views from unified turn events.
- Modify: `src/sentieon_assist/feedback_runtime.py`
  - Remove `FeedbackTurnSnapshot` and write feedback records that reference session / turn ids.
- Modify: `src/sentieon_assist/pilot_readiness.py`
  - Consume `SupportTurnView` instead of the old session-trace type.
- Modify: `src/sentieon_assist/pilot_closed_loop.py`
  - Resolve runtime feedback turns from session event logs.
- Add / Modify tests:
  - `tests/test_session_events.py`
  - `tests/test_adversarial_sessions.py`
  - `tests/test_feedback_runtime.py`
  - `tests/test_pilot_readiness.py`
  - `tests/test_pilot_closed_loop.py`
  - `tests/test_cli.py`

## Chunk 1: Introduce Unified Event Schema

### Task 1: Add the failing runtime event contract tests

**Files:**
- Add: `tests/test_session_events.py`
- Modify: `tests/test_adversarial_sessions.py`

- [ ] **Step 1: Write failing tests for session and turn event serialization**

Cover:

- creating a session record with `session_id`, `schema_version`, `git_sha`
- appending a `turn_resolved` event to `runtime/sessions/<session_id>.jsonl`
- loading the event back and deriving a `SupportTurnView`

- [ ] **Step 2: Write failing replay tests against the derived turn view**

Update replay tests so they assert against the unified turn view returned from
event-backed replay helpers, not a separate session-trace dataclass.

- [ ] **Step 3: Run focused tests to verify they fail**

Run:

- `python3.11 -m pytest -q tests/test_session_events.py tests/test_adversarial_sessions.py`

Expected:

- FAIL because `session_events.py` does not exist yet and replay still depends
  on the old trace type.

- [ ] **Step 4: Implement the minimal event schema and IO**

Add `src/sentieon_assist/session_events.py` with:

- `SupportSessionRecord`
- `SupportTurnEvent`
- `SupportTurnView`
- session file path helpers
- JSONL append / load helpers
- a view-conversion helper from `SupportTurnEvent` to `SupportTurnView`

- [ ] **Step 5: Re-run the focused tests**

Run:

- `python3.11 -m pytest -q tests/test_session_events.py tests/test_adversarial_sessions.py`

Expected: PASS

## Chunk 2: Wire CLI Sessions To Runtime Logs

### Task 2: Persist interactive chat sessions and turns

**Files:**
- Modify: `src/sentieon_assist/support_state.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add failing CLI tests for session and turn event logging**

Cover:

- chat creates a runtime session record
- each completed query appends one `turn_resolved` event
- event payload includes `raw_query`, `effective_query`, route info,
  `response_mode`, and `state_before` / `state_after`

- [ ] **Step 2: Run focused CLI tests to verify they fail**

Run:

- `python3.11 -m pytest -q tests/test_cli.py -k "session or feedback or event"`

Expected: FAIL because CLI does not yet write event logs.

- [ ] **Step 3: Add state snapshot serialization helpers**

Teach `SupportSessionState` to emit a stable JSON-safe snapshot for:

- active task
- anchor query
- confirmed facts
- open clarification slots
- last route reason

- [ ] **Step 4: Teach CLI chat to write runtime session events**

Implement:

- session creation at chat startup
- `session_started` event append
- `turn_resolved` append after each completed reply

Do not add token-level events.

- [ ] **Step 5: Re-run focused CLI tests**

Run:

- `python3.11 -m pytest -q tests/test_cli.py -k "session or feedback or event"`

Expected: PASS

## Chunk 3: Replace Feedback Snapshot Schema

### Task 3: Make runtime feedback reference session / turn ids

**Files:**
- Modify: `src/sentieon_assist/feedback_runtime.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `tests/test_feedback_runtime.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing feedback tests for event-backed feedback records**

Cover:

- `/feedback` stores `session_id` and one selected `turn_id`
- `/feedback session` stores `session_id` and all selected turn ids
- records remain scorable when `expected_mode` and `expected_task` are present

- [ ] **Step 2: Run focused feedback tests to verify they fail**

Run:

- `python3.11 -m pytest -q tests/test_feedback_runtime.py tests/test_cli.py -k "feedback"`

Expected: FAIL because feedback still stores copied `captured_turns`.

- [ ] **Step 3: Remove `FeedbackTurnSnapshot` and update record builders**

Change feedback payloads to:

- reference `session_id`
- reference `selected_turn_ids`
- optionally keep a lightweight denormalized summary

Do not keep a competing canonical turn schema under feedback records.

- [ ] **Step 4: Re-run focused feedback tests**

Run:

- `python3.11 -m pytest -q tests/test_feedback_runtime.py tests/test_cli.py -k "feedback"`

Expected: PASS

## Chunk 4: Migrate Pilot And Closed-Loop Consumers

### Task 4: Use unified turn views in readiness and closed-loop

**Files:**
- Modify: `src/sentieon_assist/pilot_readiness.py`
- Modify: `src/sentieon_assist/pilot_closed_loop.py`
- Modify: `tests/test_pilot_readiness.py`
- Modify: `tests/test_pilot_closed_loop.py`

- [ ] **Step 1: Write failing tests for pilot consumers using unified turn views**

Cover:

- readiness bucketing accepts unified turn views
- closed-loop runtime feedback loader resolves selected turns from session logs
- pending runtime feedback still counts correctly when records are unscorable

- [ ] **Step 2: Run focused pilot tests to verify they fail**

Run:

- `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py`

Expected: FAIL because pilot code still depends on old trace payloads and
`captured_turns`.

- [ ] **Step 3: Migrate readiness and closed-loop to unified views**

Update:

- readiness helpers to accept `SupportTurnView`
- runtime feedback replay to resolve turns through session event logs

- [ ] **Step 4: Re-run focused pilot tests**

Run:

- `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py`

Expected: PASS

## Chunk 5: Verify Full Runtime Contract

### Task 5: Run full regression and pilot gates

**Files:**
- Modify only if failures require a narrow fix

- [ ] **Step 1: Run targeted regression set**

Run:

- `python3.11 -m pytest -q tests/test_session_events.py tests/test_adversarial_sessions.py tests/test_feedback_runtime.py tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py tests/test_cli.py`

Expected: PASS

- [ ] **Step 2: Run full test suite**

Run:

- `python3.11 -m pytest -q`

Expected: PASS

- [ ] **Step 3: Run pilot readiness gate**

Run:

- `python3.11 scripts/pilot_readiness_eval.py`

Expected: PASS

- [ ] **Step 4: Run pilot closed loop**

Run:

- `python3.11 scripts/pilot_closed_loop.py`

Expected:

- PASS
- no regression in bucket counts
- no runtime feedback loader breakage

- [ ] **Step 5: If regressions appear, apply the minimum fix and re-run**

Only patch files directly implicated by the failure. Do not broaden scope into
RAG, platform infrastructure, or non-session UX changes.
