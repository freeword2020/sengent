# Pilot Closed-Loop Adversarial Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a closed-loop pilot adversarial layer that ingests fresh trial failures, scores current quality, compares against a baseline, and emits prioritized tightening recommendations without replacing the existing pilot-readiness gate.

**Architecture:** Keep `pilot_readiness.py` as the formal gate. Add a separate closed-loop layer that replays intake corpora, computes weighted quality metrics, compares current output to an optional baseline, and maps failure buckets to concrete tightening targets in the existing rule-first files.

**Tech Stack:** Python 3.11, pytest, local JSON corpora, deterministic routing traces, CLI scripts

---

## File Map

- Create: `docs/superpowers/specs/2026-04-09-pilot-closed-loop-adversarial-design.md`
  - Design contract for intake, score, baseline compare, and tightening guidance.
- Create: `docs/superpowers/plans/2026-04-09-pilot-closed-loop-adversarial.md`
  - Execution plan for the closed-loop trial layer.
- Create: `src/sentieon_assist/pilot_closed_loop.py`
  - Closed-loop runner, score model, baseline compare, and recommendation generation.
- Create: `scripts/pilot_closed_loop.py`
  - CLI wrapper for the closed-loop trial evaluation.
- Create: `tests/data/pilot_feedback_cases.json`
  - Single-turn real-world intake corpus.
- Create: `tests/data/pilot_feedback_sessions.json`
  - Multi-turn real-world intake corpus.
- Create: `tests/test_pilot_closed_loop.py`
  - Unit and integration tests for score, delta, intake loading, and recommendation order.
- Modify: `src/sentieon_assist/pilot_readiness.py`
  - Reuse existing report structures cleanly from the new closed-loop layer if needed.

## Chunk 1: Define the Closed-Loop Contract

### Task 1: Add failing tests for score, delta, and recommendation behavior

**Files:**
- Create: `tests/test_pilot_closed_loop.py`
- Modify: `src/sentieon_assist/pilot_readiness.py` only if shared helpers are needed

- [ ] **Step 1: Write the failing tests**

Add tests for:

- loading feedback single-turn and multi-turn corpora
- weighted score calculation
- risk-level mapping
- baseline delta calculation
- recommendation priority ordering
- closed-loop JSON serialization

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_pilot_closed_loop.py`
Expected: FAIL because the closed-loop module and corpora do not exist yet.

## Chunk 2: Implement Intake and Scoring

### Task 2: Add intake corpora and closed-loop scoring helpers

**Files:**
- Create: `src/sentieon_assist/pilot_closed_loop.py`
- Create: `tests/data/pilot_feedback_cases.json`
- Create: `tests/data/pilot_feedback_sessions.json`
- Test: `tests/test_pilot_closed_loop.py`

- [ ] **Step 1: Create minimal real-world intake corpora**

Seed them with a few real prompts already seen during trial-style testing:

- capability prompt
- `LICSRVR、Poetry`
- `短读长二倍体wgs脚本有吗`
- multi-turn WES clarify-to-script
- parameter-to-doc reset

Include:

- `id`
- `source`
- `prompt` or `turns`
- `expected_mode`
- `expected_task`
- `expected_reused_anchor` where needed

- [ ] **Step 2: Implement score and risk helpers**

Add:

- weighted bucket penalties
- `quality_score`
- `risk_level`
- bucket counts
- severe issue counters

- [ ] **Step 3: Re-run the targeted tests**

Run: `python3.11 -m pytest -q tests/test_pilot_closed_loop.py`
Expected: PASS for the unit-level score and intake tests.

## Chunk 3: Add Baseline Compare and Recommendations

### Task 3: Turn failures into next-step tightening guidance

**Files:**
- Modify: `src/sentieon_assist/pilot_closed_loop.py`
- Test: `tests/test_pilot_closed_loop.py`

- [ ] **Step 1: Add baseline compare support**

Implement:

- optional baseline JSON loading
- score delta
- bucket delta
- new failure counts

- [ ] **Step 2: Add recommendation mapping**

Map failure buckets to:

- target files
- rationale
- suggested next action

Order recommendations by severity and failure counts.

- [ ] **Step 3: Re-run targeted tests**

Run: `python3.11 -m pytest -q tests/test_pilot_closed_loop.py`
Expected: PASS

## Chunk 4: Add the Closed-Loop CLI Surface

### Task 4: Create the operator-facing script

**Files:**
- Create: `scripts/pilot_closed_loop.py`
- Modify: `src/sentieon_assist/pilot_closed_loop.py`
- Test: `tests/test_pilot_closed_loop.py`

- [ ] **Step 1: Write tests for the script-facing report shape**

Cover:

- text summary contains score and risk
- text summary contains baseline delta when provided
- text summary contains tightening recommendations
- JSON output includes gate, score, deltas, and recommendations

- [ ] **Step 2: Implement the CLI wrapper**

Support:

- `python3 scripts/pilot_closed_loop.py`
- `python3 scripts/pilot_closed_loop.py --json-out /tmp/pilot-loop.json`
- `python3 scripts/pilot_closed_loop.py --baseline /tmp/previous.json`

- [ ] **Step 3: Re-run the targeted tests**

Run: `python3.11 -m pytest -q tests/test_pilot_closed_loop.py`
Expected: PASS

## Chunk 5: Full Verification

### Task 5: Prove the closed loop does not regress the gate

**Files:**
- Modify only if regressions appear

- [ ] **Step 1: Run the new closed-loop script**

Run: `python3.11 scripts/pilot_closed_loop.py --json-out /tmp/pilot-loop.json`
Expected: PASS with score, risk, and recommendations printed.

- [ ] **Step 2: Run the formal gate again**

Run: `python3.11 scripts/pilot_readiness_eval.py`
Expected: PASS

- [ ] **Step 3: Run the full test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS

- [ ] **Step 4: If regressions appear, apply the minimum fix**

Only patch files implicated by:

- intake loading
- score logic
- baseline comparison
- recommendation formatting

Do not expand into new routing behavior unless a test proves it is necessary.
