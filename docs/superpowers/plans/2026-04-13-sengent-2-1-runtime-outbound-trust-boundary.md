# Sengent 2.1 Runtime Outbound Trust Boundary Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce runtime trust-boundary policy before hosted LLM calls so outbound prompts consume sanitized context instead of raw caller input.

**Architecture:** Keep [trust_boundary.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/trust_boundary.py) as the generic contract layer, then add a runtime-specific policy layer that sanitizes structured prompt inputs before prompt construction. Thread minimal trust-boundary summaries only through answer-bearing trace surfaces in this slice.

**Tech Stack:** Python 3.11, pytest, current `sentieon_assist` runtime/CLI modules, hosted `OpenAI-compatible` adapter path, session event logging

---

## Red Lines

- No raw caller input goes directly to hosted fallback prompt construction on covered callsites.
- No raw values from trust-boundary filtering are persisted to session traces.
- No change to runtime truth source hierarchy.
- No change to boundary pack / tool arbitration behavior.

## File Map

- Create: `src/sentieon_assist/runtime_outbound_trust.py`
- Modify: `src/sentieon_assist/trust_boundary.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/reference_intents.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/session_events.py`
- Create: `tests/test_runtime_outbound_trust.py`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_reference_intents.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_session_events.py`

## Chunk 1: Runtime Outbound Policy Layer

### Task 1: Add failing runtime trust-boundary tests

**Files:**
- Create: `tests/test_runtime_outbound_trust.py`

- [ ] **Step 1: Write failing text-sanitization tests**

Cover:

- path-like values are redacted
- email values are redacted
- secret-like key-value fragments are redacted
- active-knowledge snippets remain allowed

- [ ] **Step 2: Write failing policy-shape tests**

Cover:

- support fallback policy returns sanitized `query/info/source_context/evidence` plus `TrustBoundaryResult`
- reference fallback policy returns sanitized `query/source_context/evidence` plus `TrustBoundaryResult`
- reference-intent policy returns sanitized `query` plus `TrustBoundaryResult`

- [ ] **Step 3: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_runtime_outbound_trust.py
```

Expected: FAIL because the runtime policy layer does not exist yet.

### Task 2: Implement runtime-specific outbound trust policy helpers

**Files:**
- Create: `src/sentieon_assist/runtime_outbound_trust.py`
- Modify: `src/sentieon_assist/trust_boundary.py`

- [ ] **Step 1: Add runtime sanitization helpers**

Include:

- conservative text scrubber for path/email/secret-like fragments
- helper for dropping empty outbound fields
- helper for marking redacted vs allowed items

- [ ] **Step 2: Add policy builders**

Include:

- `build_support_fallback_outbound_context(...)`
- `build_reference_fallback_outbound_context(...)`
- `build_reference_intent_outbound_context(...)`

Each helper should return:

- sanitized structured inputs for prompt construction
- `TrustBoundaryResult`

- [ ] **Step 3: Run focused tests and verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_runtime_outbound_trust.py
```

Expected: PASS

## Chunk 2: Covered Runtime Calls Use Sanitized Context

### Task 3: Add failing integration tests for answer/reference fallback and intent parsing

**Files:**
- Modify: `tests/test_answering.py`
- Modify: `tests/test_reference_intents.py`

- [ ] **Step 1: Add failing support/reference fallback tests**

Cover:

- hosted support fallback prompt does not contain raw path/email/secret text
- hosted reference fallback prompt does not contain raw path/email/secret text

- [ ] **Step 2: Add failing reference-intent tests**

Cover:

- hosted reference-intent prompt does not contain raw path/email/secret text
- heuristic / arbitration behavior still remains unchanged

- [ ] **Step 3: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_answering.py tests/test_reference_intents.py -k "trust_boundary or hosted or outbound"
```

Expected: FAIL until callers use sanitized context.

### Task 4: Thread runtime trust-boundary policy into covered callsites

**Files:**
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/reference_intents.py`

- [ ] **Step 1: Support/reference fallback consume sanitized context**

Requirements:

- `generate_model_fallback()` uses support outbound policy before `build_support_prompt()`
- `generate_reference_fallback()` uses reference outbound policy before `build_reference_prompt()`

- [ ] **Step 2: Reference-intent parsing consumes sanitized query**

Requirements:

- `parse_reference_intent()` uses reference-intent outbound policy before `build_reference_intent_prompt()`
- heuristic fallback behavior remains unchanged on model failure

- [ ] **Step 3: Run focused tests and verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_answering.py tests/test_reference_intents.py -k "trust_boundary or hosted or outbound"
```

Expected: PASS

## Chunk 3: Minimal Trace Threading For Answer-Bearing Calls

### Task 5: Add failing trace/session tests

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_session_events.py`

- [ ] **Step 1: Add failing trace tests**

Cover:

- answer/reference fallback can pass `trust_boundary_summary` through `trace_collector`
- session events only persist sanitized trust-boundary summary

- [ ] **Step 2: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py tests/test_session_events.py -k "trust_boundary or outbound"
```

Expected: FAIL until trace threading is implemented.

### Task 6: Thread trust-boundary summary through answer-bearing trace surfaces

**Files:**
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/session_events.py`

- [ ] **Step 1: Extend answer trace shape**

Requirements:

- `SupportAnswerTrace` gets optional `trust_boundary_summary`
- fallback paths set it when outbound model call happens

- [ ] **Step 2: Persist sanitized summary in session events**

Requirements:

- `cli.run_query()` / `chat_loop()` thread the summary into `build_turn_event()`
- `build_turn_event()` stores sanitized summary only
- no raw redacted value reaches event payload

- [ ] **Step 3: Run focused tests and verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py tests/test_session_events.py -k "trust_boundary or outbound"
```

Expected: PASS

## Chunk 4: Regression And Commit

### Task 7: Run slice regression

**Files:**
- No new files

- [ ] **Step 1: Run targeted regression**

Run:

```bash
python3.11 -m pytest -q tests/test_runtime_outbound_trust.py tests/test_answering.py tests/test_reference_intents.py tests/test_cli.py tests/test_session_events.py -k "trust_boundary or outbound or hosted"
```

Expected: PASS

- [ ] **Step 2: Run main 2.1 regression**

Run:

```bash
python3.11 -m pytest -q
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/sentieon_assist/runtime_outbound_trust.py src/sentieon_assist/trust_boundary.py src/sentieon_assist/answering.py src/sentieon_assist/reference_intents.py src/sentieon_assist/cli.py src/sentieon_assist/session_events.py tests/test_runtime_outbound_trust.py tests/test_answering.py tests/test_reference_intents.py tests/test_cli.py tests/test_session_events.py docs/superpowers/specs/2026-04-13-sengent-2-1-runtime-outbound-trust-boundary-design.md docs/superpowers/plans/2026-04-13-sengent-2-1-runtime-outbound-trust-boundary.md
git commit -m "feat: enforce runtime outbound trust boundary"
```
