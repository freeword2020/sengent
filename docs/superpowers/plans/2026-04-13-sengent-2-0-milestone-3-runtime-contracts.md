# Sengent 2.0 Milestone 3 Runtime Contracts Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the runtime from a reference/troubleshooting router into a support-contract engine with explicit support intents, clarify/fallback precedence, canonical answer shapes, and runtime gap capture.

**Architecture:** Keep the current reference resolver and troubleshooting flow intact where possible, but add a thin runtime contract layer above them. Route selection should produce explicit `support_intent` and `fallback_mode` metadata, answer rendering should flow through typed answer-contract helpers, and unresolved or unsupported cases should emit structured gap records instead of ad hoc text-only clarify prompts.

**Tech Stack:** Python 3.11, pytest, existing `support_coordinator` / `answering` / `reference_resolution` runtime, session-event logging, vendor profiles

---

## Scope Boundary

This plan implements **Milestone 3 only** from the approved 2.0 spec.

This plan explicitly includes:

- explicit runtime `support_intent` metadata
- clarify / fallback precedence
- canonical boundary and knowledge-gap output shapes
- answer contracts for concept/reference, troubleshooting, decision-support, and knowledge-gap
- max clarification round enforcement using vendor clarification policy
- runtime gap record capture and trace propagation
- unsupported-version boundary handling through vendor profiles

This plan explicitly does **not** implement Milestone 4 knowledge ingestion:

- inbox ingestion of runtime gap records
- build/review/activate automation for captured gaps
- new vendor onboarding beyond Sentieon

## Chunk 1: Runtime Support Intent Contract

### Task 1: Introduce explicit support-intent and fallback metadata

**Files:**
- Create: `src/sentieon_assist/support_contracts.py`
- Modify: `src/sentieon_assist/support_state.py`
- Modify: `src/sentieon_assist/support_coordinator.py`
- Modify: `src/sentieon_assist/session_events.py`
- Test: `tests/test_support_coordinator.py`
- Test: `tests/test_adversarial_sessions.py`

- [ ] **Step 1: Write the failing route/state tests**

Add tests that prove:

- route selection produces explicit `support_intent`
- reference-style doc questions map to `concept-understanding`
- workflow guidance maps to `task-guidance` or `decision-support`
- troubleshooting stays `troubleshooting`
- clarification state tracks a round counter
- clarification rounds are capped by the vendor profile policy

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_support_coordinator.py tests/test_adversarial_sessions.py -k "intent or clarify or fallback"
```

Expected: FAIL because runtime metadata still exposes only `task` / `reason`.

- [ ] **Step 3: Add runtime support-contract types**

In `src/sentieon_assist/support_contracts.py`, define:

- `SupportIntent`
- `FallbackMode`
- `GapType`
- minimal helpers for normalization and default precedence

Keep these runtime-agnostic and separate from `ResponseMode`.

- [ ] **Step 4: Refactor coordinator/state to emit the new metadata**

Update `support_coordinator.py` and `support_state.py` so:

- `SupportRouteDecision` carries `support_intent`, `vendor_id`, `vendor_version`, and `fallback_mode`
- `SupportSessionState` tracks `clarification_rounds`
- `update_support_state()` increments rounds only when runtime leaves clarification open
- `session_events.build_turn_event()` records the intent/fallback metadata in planner payloads

Do not change the user-facing reply text in this chunk.

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run:

```bash
python3.11 -m pytest -q tests/test_support_coordinator.py tests/test_adversarial_sessions.py
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/sentieon_assist/support_contracts.py src/sentieon_assist/support_state.py src/sentieon_assist/support_coordinator.py src/sentieon_assist/session_events.py tests/test_support_coordinator.py tests/test_adversarial_sessions.py
git commit -m "feat: add runtime support intent contracts"
```

## Chunk 2: Canonical Answer Contracts And Fallback Precedence

### Task 2: Add typed answer-contract rendering for boundary, clarify, and knowledge-gap paths

**Files:**
- Create: `src/sentieon_assist/answer_contracts.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/reference_resolution.py`
- Modify: `src/sentieon_assist/trace_vocab.py`
- Test: `tests/test_answering.py`
- Test: `tests/test_reference_resolution.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing answer-contract tests**

Add tests that prove:

- unsupported version returns a boundary answer with canonical fields
- knowledge gaps return a `knowledge-gap` contract instead of a bare “需要补充” string
- repeated clarification beyond the configured max rounds falls back to `no-answer-with-boundary`
- troubleshooting clarify answers keep the existing response mode classification stable
- reference boundary answers preserve current `boundary` mode while exposing canonical fields

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_answering.py tests/test_reference_resolution.py tests/test_cli.py -k "knowledge_gap or unsupported_version or clarify_limit or boundary_contract"
```

Expected: FAIL because runtime still renders ad hoc strings and version mismatches only produce warnings.

- [ ] **Step 3: Implement answer-contract helpers**

In `src/sentieon_assist/answer_contracts.py`, add focused helpers for:

- concept/reference answers
- troubleshooting answers
- knowledge-gap answers
- boundary / no-answer answers

Each helper should render the canonical sections required by the spec while keeping the existing top-level mode headers stable enough for pilot feedback classification.

- [ ] **Step 4: Wire fallback precedence into runtime**

Update `answering.py` and `reference_resolution.py` so runtime obeys:

1. `unsupported-version`
2. `conflicting-evidence`
3. `clarification-open` (only if rounds < max)
4. `no-answer-with-boundary`

Implement at least:

- unsupported-version detection through the vendor profile
- clarify-round limit enforcement
- canonical boundary rendering
- canonical knowledge-gap rendering for missing fields / missing deterministic path

Do not add online learning or inbox writes in this chunk.

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run:

```bash
python3.11 -m pytest -q tests/test_answering.py tests/test_reference_resolution.py tests/test_cli.py -k "knowledge_gap or unsupported_version or clarify_limit or boundary_contract"
```

Expected: PASS

- [ ] **Step 6: Run compatibility regressions**

Run:

```bash
python3.11 -m pytest -q tests/test_answering.py tests/test_reference_resolution.py tests/test_support_coordinator.py tests/test_adversarial_sessions.py tests/test_cli.py
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/sentieon_assist/answer_contracts.py src/sentieon_assist/answering.py src/sentieon_assist/reference_resolution.py src/sentieon_assist/trace_vocab.py tests/test_answering.py tests/test_reference_resolution.py tests/test_cli.py
git commit -m "feat: add runtime answer contracts"
```

## Chunk 3: Runtime Gap Records And Trace Propagation

### Task 3: Capture knowledge gaps as structured runtime records

**Files:**
- Create: `src/sentieon_assist/gap_records.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/adversarial_sessions.py`
- Modify: `src/sentieon_assist/session_events.py`
- Test: `tests/test_answering.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_adversarial_sessions.py`

- [ ] **Step 1: Write the failing gap-record tests**

Add tests that prove:

- missing deterministic evidence emits a structured gap record
- unsupported-version emits a gap record with `unsupported_version`
- clarification-open emits a gap record with required missing materials
- session events preserve gap-record metadata without breaking existing turn views

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_answering.py tests/test_cli.py tests/test_adversarial_sessions.py -k "gap_record or unsupported_version or clarification_open"
```

Expected: FAIL because runtime traces currently carry only sources / boundary tags / resolver path.

- [ ] **Step 3: Implement runtime gap-record helpers**

In `src/sentieon_assist/gap_records.py`, define:

- `GapRecord`
- `build_gap_record(...)`
- normalization helpers for `gap_type`, `status`, and `known_context`

Keep the contract aligned with the spec:

- `vendor_id`
- `vendor_version`
- `intent`
- `gap_type`
- `user_question`
- `known_context`
- `missing_materials`
- `captured_at`
- `status`

- [ ] **Step 4: Propagate gap records through runtime traces**

Update `answering.py`, `cli.py`, `adversarial_sessions.py`, and `session_events.py` so:

- `SupportAnswerTrace` can carry `gap_record`
- trace collectors and turn events preserve this field
- existing consumers continue to work if `gap_record` is absent

This chunk captures records in runtime only; it does not yet append them to a knowledge inbox.

- [ ] **Step 5: Run targeted tests to verify they pass**

Run:

```bash
python3.11 -m pytest -q tests/test_answering.py tests/test_cli.py tests/test_adversarial_sessions.py -k "gap_record or unsupported_version or clarification_open"
```

Expected: PASS

- [ ] **Step 6: Run the Milestone 3 regression bucket**

Run:

```bash
python3.11 -m pytest -q tests/test_support_coordinator.py tests/test_answering.py tests/test_reference_resolution.py tests/test_cli.py tests/test_adversarial_sessions.py tests/test_pack_runtime.py tests/test_vendor_profiles.py
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/sentieon_assist/gap_records.py src/sentieon_assist/answering.py src/sentieon_assist/cli.py src/sentieon_assist/adversarial_sessions.py src/sentieon_assist/session_events.py tests/test_answering.py tests/test_cli.py tests/test_adversarial_sessions.py
git commit -m "feat: add runtime gap record capture"
```

## Final Verification

- [ ] **Step 1: Run the full Milestone 3 suite**

Run:

```bash
python3.11 -m pytest -q \
  tests/test_support_coordinator.py \
  tests/test_answering.py \
  tests/test_reference_resolution.py \
  tests/test_cli.py \
  tests/test_adversarial_sessions.py \
  tests/test_pack_runtime.py \
  tests/test_vendor_profiles.py \
  tests/test_knowledge_build.py \
  tests/test_doctor.py
```

Expected: PASS

- [ ] **Step 2: Review the runtime-contract surface**

Run:

```bash
sed -n '1,240p' docs/superpowers/specs/2026-04-12-sengent-2-0-support-kernel-design.md
sed -n '1,260p' docs/superpowers/plans/2026-04-13-sengent-2-0-milestone-3-runtime-contracts.md
sed -n '1,240p' src/sentieon_assist/support_contracts.py
sed -n '1,260p' src/sentieon_assist/answer_contracts.py
sed -n '1,220p' src/sentieon_assist/gap_records.py
```

Expected:

- runtime route metadata explicitly carries `support_intent`
- clarify / boundary / knowledge-gap paths use canonical contracts
- unsupported versions no longer degrade to soft warnings
- runtime traces can surface structured gap records
