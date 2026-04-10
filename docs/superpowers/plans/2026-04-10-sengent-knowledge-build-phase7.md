# Sengent Knowledge Build Phase 7 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add guarded activation backups and rollback so knowledge updates can revert to one of the last three active pack versions.

**Architecture:** Keep backup and rollback strictly inside the activation layer. `knowledge activate` will snapshot the current active source packs before promotion, persist a rotation-managed backup manifest, and `knowledge rollback` will restore a named backup into the active source directory without bypassing existing structured-pack boundaries.

**Tech Stack:** Python 3.11, existing CLI in `src/sentieon_assist/cli.py`, knowledge build runtime in `src/sentieon_assist/knowledge_build.py`, pytest

---

## Chunk 1: Activation Backup Contract

### Task 1: Lock backup behavior with tests

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_knowledge_build.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_cli.py`

- [ ] **Step 1: Write failing tests for activation backups**

Add tests that prove:
- `knowledge activate` stores a backup of the previous active source packs before overwriting them
- only the latest three backups are retained after repeated activations
- activation manifest records the backup id used for the activation

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py -k "backup or rollback"`
Expected: FAIL because activation backups and rollback commands do not exist yet

### Task 2: Implement activation backup rotation

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/knowledge_build.py`

- [ ] **Step 3: Add backup data structures and helpers**

Implement:
- activation backup directory under the knowledge build runtime root
- backup manifest writing
- active pack snapshot copy
- retention pruning to keep only three backups

- [ ] **Step 4: Wire backup creation into `activate_knowledge_build`**

Update activation so it:
- snapshots current active packs before copying candidate packs
- records backup metadata in `activation-manifest.json`
- leaves gate behavior unchanged

- [ ] **Step 5: Run targeted tests to verify backup behavior passes**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py -k "backup"`
Expected: PASS

## Chunk 2: Rollback Command

### Task 3: Lock rollback behavior with tests

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_knowledge_build.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_cli.py`

- [ ] **Step 6: Write failing tests for rollback**

Add tests that prove:
- `knowledge rollback --backup-id <id>` restores the matching backup into the active source directory
- rollback refuses unknown backup ids
- CLI reports the restored backup id

- [ ] **Step 7: Run targeted rollback tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py -k "rollback"`
Expected: FAIL because rollback is not implemented yet

### Task 4: Implement rollback runtime and CLI

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/knowledge_build.py`
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/cli.py`

- [ ] **Step 8: Add rollback implementation**

Implement:
- backup manifest loading
- backup-to-active restore
- rollback manifest emitted into the build runtime

- [ ] **Step 9: Add `knowledge rollback` CLI command**

Parse:
- `--build-root`
- `--backup-id`

Return clear blocked/error messages when the backup is missing.

- [ ] **Step 10: Run targeted rollback tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py -k "rollback"`
Expected: PASS

## Chunk 3: Docs And Full Verification

### Task 5: Update operator-facing docs and verify full system behavior

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`

- [ ] **Step 11: Document backup and rollback flow**

Add:
- activation backup retention policy
- rollback command contract
- operator guidance for safe apply / revert

- [ ] **Step 12: Run focused regression suites**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py`
Expected: PASS

- [ ] **Step 13: Run readiness and closed-loop regressions**

Run: `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py`
Expected: PASS

- [ ] **Step 14: Run full suite**

Run: `python3.11 -m pytest -q`
Expected: PASS

- [ ] **Step 15: Run end-to-end evaluation gates**

Run: `python3.11 scripts/pilot_readiness_eval.py`
Expected: all gates passed

Run: `python3.11 scripts/pilot_closed_loop.py`
Expected: quality score 100, risk level stable
