# Sengent 2.0 Dataset Export Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first audited dataset export chunk so reviewed gap support samples can be exported as JSONL training assets without changing runtime truth paths or the knowledge compiler flow.

**Architecture:** Keep dataset export entirely downstream of runtime and compiler. The new export module reads reviewed build artifacts plus runtime session traces, materializes `reviewed_gap_support_sample` records with provenance and expected answer contract fields, and exposes a read-only CLI export command.

**Tech Stack:** Python 3.11, pytest, existing build artifacts (`gap_intake_review.jsonl`, `gap_eval_seed.jsonl`, `incident-memory.json`), runtime session logs, YAML sidecars, local JSONL export

---

## Scope Boundary

This phase implements the first complete chunk of the roadmap’s dataset export work.

This phase explicitly includes:

- a reviewed-gap dataset export contract
- JSONL export of reviewed gap support samples
- CLI `knowledge export-dataset`
- provenance / review / expected answer contract preservation
- focused docs and tests

This phase explicitly does **not** include:

- training execution
- runtime dataset consumption
- online learning
- broader incident/playbook exemplar export
- runtime feedback export without an explicit maintainer-reviewed contract

## File Map

- Create: `src/sentieon_assist/dataset_export.py`
  - load reviewed gap artifacts
  - resolve selected session turns
  - assemble audited dataset samples
  - write JSONL and format export summary
- Modify: `src/sentieon_assist/cli.py`
  - add `knowledge export-dataset`
  - parse `--output`, `--build-id`, `--build-root`, `--runtime-root`
  - wire summary output
- Create: `tests/test_dataset_export.py`
  - direct export contract coverage
- Modify: `tests/test_cli.py`
  - CLI export coverage
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
  - only if the export command materially changes the maintainer flow wording

## Chunk 1: Lock The Audited Export Contract

### Task 1: Write failing tests for reviewed gap export

**Files:**
- Create: `tests/test_dataset_export.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add export contract tests**

Add tests that prove:

- only `seed_eval` reviewed gaps export as dataset samples
- each exported sample includes:
  - `sample_id`
  - `sample_type`
  - `build_id`
  - `vendor_id`
  - `review_status`
  - `review_decision`
  - `expected_answer_contract`
  - `incident`
  - `support_trace`
  - `source_artifacts`
- exported traces come from selected runtime session turns

- [ ] **Step 2: Add CLI export tests**

Add tests that prove:

- `sengent knowledge export-dataset --output <path>` exports from the latest build
- explicit `--build-id`, `--build-root`, and `--runtime-root` are honored
- CLI summary reports build id, exported count, skipped count, and output path

- [ ] **Step 3: Run targeted tests to confirm failure**

Run:

```bash
python3.11 -m pytest -q tests/test_dataset_export.py tests/test_cli.py -k "dataset_export or export_dataset"
```

Expected: FAIL because the export module and CLI command do not exist yet.

## Chunk 2: Implement Reviewed Gap Dataset Export

### Task 2: Add dataset export module and CLI wiring

**Files:**
- Create: `src/sentieon_assist/dataset_export.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Implement build artifact loaders**

Load:

- `gap_intake_review.jsonl`
- `gap_eval_seed.jsonl`
- `candidate-packs/incident-memory.json`
- metadata sidecars referenced by review records
- runtime session logs for selected turns

- [ ] **Step 2: Implement sample assembly**

Assemble `reviewed_gap_support_sample` records that preserve:

- review provenance
- expected answer contract
- incident context
- selected support trace
- source artifact paths

- [ ] **Step 3: Implement exporter and summary formatter**

Write JSONL to the requested output path and report:

- build id
- exported count
- skipped count
- output path

- [ ] **Step 4: Add CLI command**

Support:

- `sengent knowledge export-dataset --output <path>`
- `sengent knowledge export-dataset --output <path> --build-id <id>`
- `sengent knowledge export-dataset --output <path> --build-root <dir> --runtime-root <dir>`

- [ ] **Step 5: Run targeted tests to verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_dataset_export.py tests/test_cli.py -k "dataset_export or export_dataset"
```

Expected: PASS

## Chunk 3: Verification And Closeout

### Task 3: Fresh verification and commit

**Files:**
- Verify: `tests/test_dataset_export.py`
- Verify: `tests/test_cli.py`
- Verify: `tests/test_knowledge_build.py`
- Verify: `tests/test_gap_review.py`
- Verify: `tests/test_pilot_closed_loop.py`
- Verify: `tests/test_docs_contract.py`

- [ ] **Step 1: Run focused verification**

Run:

```bash
python3.11 -m pytest -q tests/test_dataset_export.py tests/test_cli.py tests/test_knowledge_build.py tests/test_gap_review.py tests/test_pilot_closed_loop.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 2: Run broader regression verification**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_gap_intake.py tests/test_source_intake.py tests/test_dataset_export.py tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py tests/test_answering.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_pilot_closed_loop.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-13-sengent-2-0-dataset-export-design.md docs/superpowers/plans/2026-04-13-sengent-2-0-dataset-export.md src/sentieon_assist/dataset_export.py src/sentieon_assist/cli.py tests/test_dataset_export.py tests/test_cli.py
git commit -m "feat: add reviewed dataset export"
```
