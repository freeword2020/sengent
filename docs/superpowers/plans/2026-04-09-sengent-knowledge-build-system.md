# Sengent Knowledge Build System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first P0 knowledge build pipeline that turns inboxed raw docs into canonical build artifacts, candidate knowledge packs, and maintainer-facing reports without changing the current runtime answer path.

**Architecture:** Add a dedicated `knowledge build` flow alongside the current support CLI. The flow scans a local inbox, parses supported files through a parser adapter layer with optional Docling support, writes canonical JSONL artifacts and exception queues into `runtime/knowledge-build/`, then compiles candidate packs and a review report. Runtime support answering continues to use the existing `sentieon-note/*.json` active packs until a future activation step.

**Tech Stack:** Python 3.11, existing `sentieon_assist` CLI package, `pytest`, local filesystem JSONL artifacts, optional `docling` import when available

---

## Chunk 1: CLI Entry And Build Runtime

### Task 1: Add failing CLI tests for `knowledge build`

**Files:**
- Create: `tests/test_knowledge_build.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Write the failing test**

Add tests that expect:
- `main(["knowledge", "build", "--inbox-dir", ..., "--build-root", ...])` returns `0`
- build command creates a new build directory under the requested runtime root
- build command prints a maintainer-facing summary instead of raw internals

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k cli`
Expected: FAIL because `knowledge build` command does not exist yet

- [ ] **Step 3: Write minimal implementation**

Add a `knowledge build` branch in `src/sentieon_assist/cli.py` that delegates to a new knowledge build orchestrator module.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k cli`
Expected: PASS

## Chunk 2: Canonical Schema And Parser Adapters

### Task 2: Add failing tests for inventory, canonical records, and parser fallback behavior

**Files:**
- Modify: `tests/test_knowledge_build.py`
- Create: `src/sentieon_assist/knowledge_build.py`

- [ ] **Step 1: Write the failing test**

Add tests that expect:
- inbox scan records file path, detected file type, product scope, and missing metadata warnings
- supported text-like files (`.md`, `.txt`, `.sh`, `.json`, `.html`) emit canonical document and section records
- PDF files without Docling installed are queued as exceptions instead of crashing the build
- parser selection reports whether `docling` was available

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k canonical`
Expected: FAIL because no knowledge build runtime exists

- [ ] **Step 3: Write minimal implementation**

In `src/sentieon_assist/knowledge_build.py` add:
- build id / runtime path helpers
- dataclasses for source inventory, canonical document records, canonical section records, build exceptions, and build summary
- parser adapter interface
- built-in plain-text parser
- optional Docling adapter that activates only if import succeeds

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k canonical`
Expected: PASS

## Chunk 3: Candidate Pack Compiler And Maintainer Report

### Task 3: Add failing tests for candidate pack output and exception-first reporting

**Files:**
- Modify: `tests/test_knowledge_build.py`
- Modify: `src/sentieon_assist/knowledge_build.py`

- [ ] **Step 1: Write the failing test**

Add tests that expect:
- every build writes `inventory.json`, `canonical_doc_record.jsonl`, `canonical_section_record.jsonl`, `exceptions.jsonl`, and `report.md`
- build output includes a `candidate-packs/` directory with P0 candidate copies of the current runtime packs plus a build manifest
- report surfaces parse failures / missing metadata before generic counts
- report clearly states that candidate packs are not yet active runtime packs

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k report`
Expected: FAIL because report and candidate pack compilation are incomplete

- [ ] **Step 3: Write minimal implementation**

Extend `src/sentieon_assist/knowledge_build.py` to:
- copy current `sentieon-note/*.json` packs into `candidate-packs/`
- emit build manifest and source coverage summary
- write an exception-first `report.md`
- keep all build artifacts under `runtime/knowledge-build/<build_id>/`

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k report`
Expected: PASS

## Chunk 4: Gate Hooks And Regression Coverage

### Task 4: Add failing tests for gate hook wiring and maintainer-safe behavior

**Files:**
- Modify: `tests/test_knowledge_build.py`
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Write the failing test**

Add tests that expect:
- build summary includes the exact gate commands maintainers or owners should run next
- build command never mutates active `sentieon-note/*.json`
- unsupported files or parse failures do not abort the whole build

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k gate`
Expected: FAIL because gate guidance and non-destructive guarantees are not fully wired

- [ ] **Step 3: Write minimal implementation**

Finish the build orchestrator so it:
- reports gate commands
- preserves active packs untouched
- treats failures as queued exceptions unless the build root itself is invalid

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k gate`
Expected: PASS

## Chunk 5: Full Verification

### Task 5: Verify the new build flow without regressing current support behavior

**Files:**
- Test: `tests/test_knowledge_build.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Run focused suite**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py`
Expected: PASS

- [ ] **Step 2: Run full test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS

- [ ] **Step 3: Run pilot readiness gate**

Run: `python3.11 scripts/pilot_readiness_eval.py`
Expected: All gates pass

- [ ] **Step 4: Run pilot closed loop**

Run: `python3.11 scripts/pilot_closed_loop.py`
Expected: `Quality score: 100`, `Risk level: stable`

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md docs/superpowers/plans/2026-04-09-sengent-knowledge-build-system.md src/sentieon_assist/cli.py src/sentieon_assist/knowledge_build.py tests/test_knowledge_build.py tests/test_cli.py
git commit -m "feat: add knowledge build pipeline scaffolding"
```
