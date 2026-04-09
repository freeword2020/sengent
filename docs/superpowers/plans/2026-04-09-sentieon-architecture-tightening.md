# Sentieon Architecture Tightening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten the current `Sengent` rule-first architecture so top-level routing stays in the coordinator, while reference-domain subtype recognition moves back into the reference-intent layer.

**Architecture:** Keep the existing CLI, support coordinator, deterministic reference indices, and answer pipeline. Contract the current responsibilities by teaching `reference_intents.py` to recognize operational doc-style and selected boundary-prone reference prompts, then simplify `support_coordinator.py` so it only decides top-level support tasks and follow-up reuse.

**Tech Stack:** Python 3.11, pytest, local JSON knowledge files, deterministic routing helpers

---

## File Map

- Modify: `src/sentieon_assist/reference_intents.py`
  - Add deterministic heuristics for operational doc-style reference prompts and selected boundary-prone prompts.
- Modify: `src/sentieon_assist/support_coordinator.py`
  - Remove coordinator-local reference subtype branches that belong to the reference-intent layer.
- Modify: `tests/test_reference_intents.py`
  - Add intent-level regressions for doc-style and boundary-prone reference prompts.
- Modify: `tests/test_support_coordinator.py`
  - Add top-level route regressions proving these prompts still land in `reference_lookup` after coordinator simplification.

## Chunk 1: Tighten Reference Intent Ownership

### Task 1: Add failing tests for reference-domain subtype detection

**Files:**
- Modify: `tests/test_reference_intents.py`
- Modify: `tests/test_support_coordinator.py`

- [ ] **Step 1: Write the failing tests**

Add intent tests for:

- CPU / thread-utilization prompt -> `reference_other`
- `LICCLNT` / `LICSRVR` tool-selection prompt -> `reference_other`
- `BWA-turbo` prompt -> `reference_other`

Add coordinator tests for:

- the same prompts still route to `reference_lookup`
- route reason now comes from parsed reference intent, not coordinator-only
  subtype branches

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_reference_intents.py tests/test_support_coordinator.py -k "reference_other or route"`
Expected: FAIL because the current coordinator still owns these subtype checks
and `parse_reference_intent()` does not classify them consistently.

- [ ] **Step 3: Teach `reference_intents.py` the missing subtype heuristics**

Add small deterministic helpers for:

- operational doc-style prompts
- license-doc prompts
- selected boundary-prone prompts that should still remain inside
  `reference_lookup`

Return `ReferenceIntent(intent="reference_other", ...)` for these prompts.

- [ ] **Step 4: Re-run the targeted tests**

Run: `python3.11 -m pytest -q tests/test_reference_intents.py tests/test_support_coordinator.py -k "reference_other or route"`
Expected: PASS

## Chunk 2: Simplify Top-Level Coordinator

### Task 2: Remove coordinator-local reference subtype ownership

**Files:**
- Modify: `src/sentieon_assist/support_coordinator.py`
- Test: `tests/test_support_coordinator.py`

- [ ] **Step 1: Remove now-redundant coordinator helpers**

Delete or stop using:

- coordinator-local operational doc detection
- coordinator-local license doc detection
- coordinator-local `BWA-turbo` / `SVSolver` boundary special-cases
- coordinator-local boundary-tag routing

Keep:

- capability-question detection
- troubleshooting precedence
- onboarding-guidance routing
- reference-task fallback via parsed reference intent

- [ ] **Step 2: Run focused coordinator tests**

Run: `python3.11 -m pytest -q tests/test_support_coordinator.py -v`
Expected: PASS

- [ ] **Step 3: Run related reference tests**

Run: `python3.11 -m pytest -q tests/test_reference_intents.py tests/test_cli.py -k "reference_other or capability or workflow_guidance"`
Expected: PASS

## Chunk 3: Verify No Coverage Regressions

### Task 3: Run full regression and adversarial drill

**Files:**
- Modify: none unless regressions appear

- [ ] **Step 1: Run full test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS with all tests green

- [ ] **Step 2: Run adversarial support drill**

Run: `python3.11 scripts/adversarial_support_drill.py`
Expected: PASS with all adversarial cases green

- [ ] **Step 3: If regressions appear, apply the minimum fix**

Only patch files directly implicated by the failure. Do not broaden scope into
retrieval redesign or answer-style refactoring.

- [ ] **Step 4: Re-run verification**

Run:

- `python3.11 -m pytest -q`
- `python3.11 scripts/adversarial_support_drill.py`

Expected: PASS
