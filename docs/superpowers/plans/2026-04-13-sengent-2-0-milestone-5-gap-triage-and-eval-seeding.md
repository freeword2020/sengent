# Sengent 2.0 Milestone 5 Gap Triage And Eval Seeding Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `gap_intake_review.jsonl` from a passive build artifact into an explicit offline maintainer workflow that records triage decisions in inbox metadata, derives eval seeds for reviewed gaps, and keeps activation behind the existing build / review / gate / activate flow.

**Architecture:** Keep runtime gap capture and candidate incident compilation exactly offline. Phase 5 adds a maintainer-owned review contract on top of incident gap inbox entries: build emits pending-review records, `knowledge triage-gap` writes decisions back into sidecar metadata, rebuild materializes decision-aware `gap_intake_review.jsonl` rows plus `gap_eval_seed.jsonl`, and operators can feed those seeds into the existing closed-loop gate before any activation.

**Tech Stack:** Python 3.11, pytest, existing `knowledge build` / `knowledge review` / `pilot_closed_loop` pipeline, YAML sidecars, local JSONL review artifacts

---

## Scope Boundary

This plan implements **Phase 5 only** on top of the completed Milestone 4 gap intake flow.

This plan explicitly includes:

- a formal maintainer review metadata contract for runtime gap intake entries
- a CLI command for writing gap triage / decision state back into inbox sidecars
- decision-aware `gap_intake_review.jsonl` records with pending / triaged / seeded visibility
- a derived eval seed artifact that reuses the existing runtime feedback JSONL contract
- review report and operator-manual updates that preserve `build -> review -> gate -> activate`

This plan explicitly does **not** include:

- automatic activation of reviewed gaps
- direct runtime consumption changes
- automatic online learning or prompt mutation
- auto-writing eval cases into the committed pilot corpora

## File Map

- Create: `src/sentieon_assist/gap_review.py`
  - normalize and validate maintainer review metadata
  - update sidecar metadata for a reviewed gap entry
  - derive runtime-feedback-compatible eval seed records from approved review decisions
- Modify: `src/sentieon_assist/knowledge_build.py`
  - enrich `GapIntakeReviewRecord` with maintainer review state and source metadata path
  - emit `gap_eval_seed.jsonl`
  - surface pending / decisioned / seeded counts in `report.md`
  - keep candidate packs explicitly non-active until gate + activation
- Modify: `src/sentieon_assist/cli.py`
  - add `knowledge triage-gap`
  - parse `--build-id`, `--build-root`, `--entry-id`, `--decision`, `--status`, `--expected-mode`, `--expected-task`, `--scope`, `--note`
  - reject invalid decision payloads such as `seed_eval` without expected mode/task
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
  - document the maintainer triage loop and the gate command that consumes `gap_eval_seed.jsonl`
- Create: `tests/test_gap_review.py`
  - focused review-contract and sidecar-update coverage
- Modify: `tests/test_knowledge_build.py`
  - build artifact, report, and eval-seed generation coverage
- Modify: `tests/test_cli.py`
  - CLI `knowledge triage-gap` coverage

## Chunk 1: Review Contract And Sidecar Decision Writer

### Task 1: Define the maintainer review metadata contract and make it writable from CLI

**Files:**
- Create: `src/sentieon_assist/gap_review.py`
- Modify: `src/sentieon_assist/cli.py`
- Test: `tests/test_gap_review.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing review-contract tests**

Add tests that prove:

- gap review metadata defaults to a pending state when an intake entry has never been triaged
- `knowledge triage-gap` writes a `maintainer_review` block into the source `.meta.yaml`
- `seed_eval` decisions require both `expected_mode` and `expected_task`
- repeated triage updates overwrite only the review block and preserve the existing gap metadata

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_cli.py -k "triage_gap or maintainer_review"
```

Expected: FAIL because there is no maintainer review helper module or `knowledge triage-gap` command yet.

- [ ] **Step 3: Implement the review helper module**

In `src/sentieon_assist/gap_review.py`, add:

- a normalized `maintainer_review` contract with defaults:
  - `status: pending`
  - `decision: pending`
  - `scope: last`
  - `expected_mode: ""`
  - `expected_task: ""`
  - `notes: ""`
- validation helpers for supported decisions and seed-eval requirements
- a sidecar updater that writes only the review block back to YAML

- [ ] **Step 4: Add the CLI command**

In `src/sentieon_assist/cli.py`:

- extend help text with `triage-gap`
- add option parsing for:
  - `--build-id`
  - `--build-root`
  - `--entry-id`
  - `--decision`
  - `--status`
  - `--expected-mode`
  - `--expected-task`
  - `--scope`
  - `--note`
- resolve the selected gap from the build’s `gap_intake_review.jsonl`
- write the decision back into the source sidecar metadata

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_cli.py -k "triage_gap or maintainer_review"
```

Expected: PASS

## Chunk 2: Decision-Aware Build Artifacts And Eval Seed Materialization

### Task 2: Make `knowledge build` turn maintainer decisions into formal review and eval artifacts

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Create: `tests/test_gap_review.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing build tests**

Add tests that prove:

- `gap_intake_review.jsonl` includes pending review defaults for untouched gap entries
- triaged entries surface:
  - `review_status`
  - `review_decision`
  - `review_scope`
  - `review_notes`
  - source metadata path
- `seed_eval` decisions emit `gap_eval_seed.jsonl`
- seeded eval rows reuse the runtime feedback JSONL contract:
  - `record_id`
  - `source`
  - `scope`
  - `session_id`
  - `selected_turn_ids`
  - `expected_mode`
  - `expected_task`
  - `scorable`

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_gap_review.py -k "gap_eval_seed or gap_intake_review"
```

Expected: FAIL because the build currently emits only raw captured-gap rows and no eval seed artifact.

- [ ] **Step 3: Extend the build review contract**

In `src/sentieon_assist/knowledge_build.py`:

- enrich `GapIntakeReviewRecord` with:
  - `session_id`
  - `turn_id`
  - `metadata_path`
  - `review_status`
  - `review_decision`
  - `review_scope`
  - `review_notes`
  - `expected_mode`
  - `expected_task`
- read and normalize the `maintainer_review` block from incident metadata
- keep entries without review decisions as `pending`

- [ ] **Step 4: Emit eval seeds and report sections**

Still in `knowledge_build.py`:

- add `GapEvalSeedRecord`
- write `gap_eval_seed.jsonl` into the build directory
- add report counts for:
  - pending triage
  - triaged decisions
  - eval seeds materialized
- include the exact closed-loop command that can consume `gap_eval_seed.jsonl`

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run:

```bash
python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_gap_review.py -k "gap_eval_seed or gap_intake_review"
```

Expected: PASS

## Chunk 3: Operator Flow And End-To-End Review Loop

### Task 3: Document and verify the maintainer review -> gate handoff

**Files:**
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Update the operator manual**

Document:

- `knowledge intake-gap` creates a pending incident intake entry
- `knowledge build` exposes `gap_intake_review.jsonl` and `gap_eval_seed.jsonl`
- `knowledge triage-gap` is the maintainer step that writes review decisions back into inbox metadata
- eval seeds are fed into the existing closed-loop gate before activation
- activation still remains manual and blocked on gate success

- [ ] **Step 2: Add one end-to-end workflow test**

Add a test that:

- exports a runtime gap into the inbox
- runs `knowledge build`
- runs `knowledge triage-gap --decision seed_eval --expected-mode <...> --expected-task <...>`
- rebuilds
- verifies the rebuilt `gap_intake_review.jsonl` row is triaged
- verifies `gap_eval_seed.jsonl` contains exactly one scorable seed row for the selected turn

- [ ] **Step 3: Run the end-to-end slice**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py tests/test_knowledge_build.py -k "triage_gap_end_to_end or gap_eval_seed"
```

Expected: PASS

- [ ] **Step 4: Run the focused Phase 5 verification suite**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_gap_intake.py tests/test_cli.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_pilot_closed_loop.py
```

Expected: PASS
