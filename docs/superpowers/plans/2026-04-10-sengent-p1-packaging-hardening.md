# Sengent P1 Packaging Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten Sengent for intranet packaging by making dependency requirements explicit, blocking incomplete managed-pack activation/build states, and surfacing packaging preflight health in `doctor`.

**Architecture:** Keep the current rule-first runtime and renew pipeline unchanged in shape. Add a small packaging contract layer around it: packaging metadata declares the true mandatory and optional dependencies, managed pack directories must be complete before build/activate/rollback, and `doctor` becomes the human-readable preflight for deployment and operator use.

**Tech Stack:** Python 3.11, setuptools/`pyproject.toml`, installed `sengent` CLI, `pytest`, local filesystem JSON/JSONL artifacts, optional `docling`.

---

## Chunk 1: Packaging Contract

### Task 1: Declare actual build/runtime dependencies

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/pyproject.toml`
- Test: `/Users/zhuge/Documents/codex/harness/tests/test_packaging_contract.py`

- [ ] **Step 1: Write the failing packaging contract test**

Add a test that parses `pyproject.toml` with `tomllib` and asserts:
- `PyYAML` is a mandatory dependency
- `docling` is declared as an optional extra for PDF knowledge build support

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_packaging_contract.py`
Expected: FAIL because the current project metadata only declares `rich`.

- [ ] **Step 3: Update packaging metadata**

Adjust `pyproject.toml` so that:
- `PyYAML` is part of `[project].dependencies`
- `docling` is exposed through `[project.optional-dependencies]`

- [ ] **Step 4: Run the packaging test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_packaging_contract.py`
Expected: PASS

## Chunk 2: Managed Pack Completeness Guards

### Task 2: Block build/activate/rollback when managed pack sets are incomplete

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/knowledge_build.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_knowledge_build.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_cli.py`

- [ ] **Step 1: Write failing guard tests**

Add tests that prove:
- `knowledge build` refuses an incomplete active source pack directory
- `knowledge activate` refuses a candidate build whose `candidate-packs/` misses any managed pack
- `knowledge rollback` refuses an invalid backup manifest or incomplete backup pack set

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py -k "incomplete_source_pack_set or incomplete_candidate_pack_set or invalid_backup_pack_set"`
Expected: FAIL with missing guard coverage.

- [ ] **Step 3: Implement minimal completeness validation**

In `knowledge_build.py`:
- add a single-source helper for managed pack completeness
- validate active source packs before build
- validate candidate packs and active source packs before activate
- validate rollback backups before restore

- [ ] **Step 4: Re-run the targeted tests**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py -k "incomplete_source_pack_set or incomplete_candidate_pack_set or invalid_backup_pack_set"`
Expected: PASS

## Chunk 3: Doctor Preflight

### Task 3: Surface packaging and renew preflight health in `doctor`

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/doctor.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_doctor.py`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`

- [ ] **Step 1: Write failing doctor tests**

Add tests that require `doctor` to report:
- whether `docling` is installed
- whether the active source directory has a complete managed pack set
- which pack files are missing when it is incomplete

- [ ] **Step 2: Run the doctor tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_doctor.py`
Expected: FAIL because the current report does not include packaging/build health.

- [ ] **Step 3: Implement the minimal preflight report**

Extend `gather_doctor_report()` and `format_doctor_report()` so operators can see:
- build runtime support status
- PDF parser optional capability
- managed pack completeness health

Keep the report concise and operator-readable.

- [ ] **Step 4: Update docs**

Document:
- `PyYAML` as mandatory
- `docling` as optional PDF capability
- `doctor` as the first preflight before intranet packaging or renew operations

- [ ] **Step 5: Re-run the doctor tests**

Run: `python3.11 -m pytest -q tests/test_doctor.py`
Expected: PASS

## Chunk 4: Full Verification

### Task 4: Verify the full P1 hardening set

**Files:**
- Verify only

- [ ] **Step 1: Run focused regression suites**

Run: `python3.11 -m pytest -q tests/test_packaging_contract.py tests/test_knowledge_build.py tests/test_cli.py tests/test_doctor.py`
Expected: PASS

- [ ] **Step 2: Run renew/runtime safety suites**

Run: `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS

- [ ] **Step 4: Run gate scripts**

Run:
- `python3.11 scripts/pilot_readiness_eval.py`
- `python3.11 scripts/pilot_closed_loop.py`

Expected:
- all gates pass
- no new tightening recommendations caused by the P1 hardening
