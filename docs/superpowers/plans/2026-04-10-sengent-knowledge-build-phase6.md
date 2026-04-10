# Sengent Knowledge Build Phase 6 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make knowledge add/update/delete workflows maintainers-first by adding scaffolded source creation, explicit delete/tombstone compilation, and a simple review entrypoint that surfaces the latest build state without requiring people to inspect raw artifacts by hand.

**Architecture:** Keep Sengent's runtime and evaluation path unchanged. Phase 6 continues to strengthen only the offline knowledge-build system: `knowledge scaffold` creates safe source templates, `knowledge build` understands explicit `action: delete` retirement requests, and `knowledge review` prints the latest build report so maintainers can operate the compiler without touching runtime JSON files directly.

**Tech Stack:** Python 3.11, existing `sentieon_assist` CLI package, `pytest`, local JSON/JSONL artifacts, YAML sidecar metadata, markdown source stubs

---

## Chunk 1: Maintainer CLI Entry Points

### Task 1: Add failing tests for scaffold and review commands

**Files:**
- Modify: `tests/test_cli.py`
- Reference: `src/sentieon_assist/cli.py`
- Reference: `src/sentieon_assist/knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- `knowledge scaffold --kind module --id fastdedup --name FastDedup` creates:
  - `knowledge-inbox/<product>/fastdedup.md`
  - `knowledge-inbox/<product>/fastdedup.meta.yaml`
- rerunning scaffold for an existing source preserves markdown content and only fills missing metadata defaults
- `knowledge scaffold --kind module --id fastdedup --action delete` creates a retirement stub with `action: delete`
- `knowledge review` prints the latest build report when a build already exists

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_cli.py -k "knowledge_scaffold or knowledge_review"`
Expected: FAIL because phase-5 CLI has no scaffold/review commands

## Chunk 2: Delete/Tombstone Compilation

### Task 2: Add explicit delete action support to candidate-pack compilation

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- a markdown or scaffolded stub with metadata `action: delete` removes the target id from the candidate pack
- candidate manifest diffs include `removed_ids`
- report surfaces removed ids in changed candidate packs
- delete records require only the minimal metadata needed for safe removal:
  - `pack_target`
  - `entry_type` (or derived equivalent)
  - `id`

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "delete_action or removed_ids"`
Expected: FAIL because phase-5 compiler only upserts entries

- [ ] **Step 3: Implement conservative delete handling**

In `src/sentieon_assist/knowledge_build.py`:
- accept `action: delete` in source metadata
- compile delete records into candidate-pack removals rather than upserts
- update pack diffs and report output to include removed ids
- keep delete handling explicit and local to candidate packs; do not touch active packs until gated activation

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "delete_action or removed_ids"`
Expected: PASS

## Chunk 3: Safe Source Scaffolding

### Task 3: Implement scaffold helpers for add/update/delete workflows

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- `knowledge scaffold` derives `pack_target`/`entry_type` from `--kind`
- upsert scaffolds include a markdown stub plus metadata template
- delete scaffolds include a retirement markdown stub and `action: delete`
- existing markdown is not overwritten on rerun
- existing sidecar metadata preserves user-edited values while backfilling missing keys

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_cli.py -k "knowledge_scaffold"`
Expected: FAIL because scaffold helpers do not exist yet

- [ ] **Step 3: Implement the minimal foolproof scaffold flow**

In `src/sentieon_assist/knowledge_build.py` and `src/sentieon_assist/cli.py`:
- add scaffold helpers and a CLI command
- support kinds:
  - `module`
  - `workflow`
  - `external-format`
  - `external-tool`
  - `external-error`
- create safe defaults for markdown body and sidecar metadata
- preserve existing user content on rerun

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_cli.py -k "knowledge_scaffold"`
Expected: PASS

## Chunk 4: Review Entry Point And Full Verification

### Task 4: Expose a review command and verify phase 6 end-to-end

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`
- Modify: `docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase6.md`
- Test: `tests/test_knowledge_build.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_pilot_readiness.py`
- Test: `tests/test_pilot_closed_loop.py`

- [ ] **Step 1: Implement `knowledge review`**

Provide a CLI command that:
- finds the latest build by default
- optionally accepts `--build-id`
- prints the build report and relevant build path

- [ ] **Step 2: Run focused knowledge-build coverage**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py`
Expected: PASS

- [ ] **Step 3: Run focused pilot coverage**

Run: `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS

- [ ] **Step 5: Run pilot gates**

Run: `python3.11 scripts/pilot_readiness_eval.py`
Expected: PASS

Run: `python3.11 scripts/pilot_closed_loop.py`
Expected: PASS with stable risk output

- [ ] **Step 6: Update docs to reflect the maintainer workflow**

Reflect the phase-6 additions in the design doc:
- `knowledge scaffold`
- `action: delete` retirement flow
- `knowledge review`
- add/update/delete maintenance path that avoids manual pack editing
