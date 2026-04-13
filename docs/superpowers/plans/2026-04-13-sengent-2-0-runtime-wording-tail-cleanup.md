# Runtime Wording Tail Cleanup Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans or superpowers:subagent-driven-development. Follow strict TDD. Do not widen scope beyond `chat_events.py`, `cli.py`, and the directly related tests.

**Goal:** Finish the remaining runtime wording tail by routing chat event field labels through vendor-owned wording assets and explicitly threading vendor context into the CLI capability path.

**Architecture:** Reuse the existing `VendorProfile.runtime_wording` contract. Do not introduce a new wording registry or new decoupling layer. Keep Sentieon-first defaults unchanged.

**Tech Stack:** Python 3.11, pytest, existing vendor profile registry, current CLI runtime

---

## Scope Boundary

This plan includes only:

- `chat_events.py` missing-info field labels
- `cli.py` capability vendor threading
- focused regression tests

This plan excludes:

- query lexicon updates
- compile heuristics
- rules/source payload rewrites
- truth path / activate / rollback
- broad CLI wording cleanup

## File Map

- Modify: `src/sentieon_assist/chat_events.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `tests/test_chat_ui.py`
- Modify: `tests/test_cli.py`

## Chunk 1: Lock The Tail In Tests

### Task 1: Add failing tests

- [ ] Add a `test_chat_ui.py` case proving `event_check_missing_info()` can render profile-owned field labels when given an explicit `vendor_id`.
- [ ] Add a `test_cli.py` case proving `run_query()` passes `decision.vendor_id` into `format_capability_explanation_answer()`.
- [ ] Run:

```bash
python3.11 -m pytest -q tests/test_chat_ui.py -k "missing_info or event_"
python3.11 -m pytest -q tests/test_cli.py -k "capability"
```

Expected before implementation: FAIL for the new tests because `event_check_missing_info()` does not yet accept vendor context and `run_query()` does not yet pass `decision.vendor_id`.

## Chunk 2: Implement The Minimal Tail Cleanup

### Task 2: Reuse the existing wording contract

- [ ] In `chat_events.py`, replace local field-label ownership with a thin vendor-profile lookup helper.
- [ ] Keep `event_check_missing_info()` text template unchanged.
- [ ] Keep default behavior Sentieon-first.
- [ ] In `cli.py`, pass `decision.vendor_id` to `format_capability_explanation_answer()`.

## Chunk 3: Focused Regression

### Task 3: Prove the tail is closed

- [ ] Run:

```bash
python3.11 -m pytest -q tests/test_chat_ui.py -k "missing_info or event_"
python3.11 -m pytest -q tests/test_cli.py -k "capability"
python3.11 -m pytest -q tests/test_answering.py -k "capability"
```

Expected: PASS

## Non-Goals During Execution

Do not:

- edit `answering.py`
- edit vendor profiles
- edit source/rule content
- sweep other chat/CLI wording
- add a new contract beyond the existing `runtime_wording.field_labels`
