# Sengent 2.0 Source Intake Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first `Knowledge Factory` source-intake command so maintainers can import local materials into inbox-ready artifacts with provenance and review hints instead of building those files by hand.

**Architecture:** Keep the runtime and active-knowledge path unchanged. This phase adds a factory-side adapter that wraps the existing scaffold contract: `knowledge intake-source` reads a local text-like file, writes imported content into the inbox markdown body, and enriches the sidecar with source-class provenance plus maintainer review hints.

**Tech Stack:** Python 3.11, pytest, existing `knowledge scaffold` / `knowledge build` pipeline, YAML sidecars, local filesystem source files

---

## File Map

- Create: `src/sentieon_assist/source_intake.py`
  - validate source classes
  - load supported local file types
  - generate imported markdown body
  - merge scaffold metadata with provenance and review hints
- Modify: `src/sentieon_assist/cli.py`
  - add `knowledge intake-source`
  - parse CLI options
  - print created artifact paths
- Create: `tests/test_source_intake.py`
  - source-intake module coverage
- Modify: `tests/test_cli.py`
  - CLI coverage for `knowledge intake-source`

## Task 1: Lock the source-intake contract with tests

**Files:**
- Create: `tests/test_source_intake.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Add tests that prove:

- supported source classes normalize correctly
- unsupported file types are rejected
- intake writes a markdown artifact that includes provenance and imported content
- sidecar metadata includes:
  - `origin: factory-source-intake`
  - `source_class`
  - `source_provenance`
  - `review_hints`
- CLI `knowledge intake-source` writes the artifacts via the default scaffold flow

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_source_intake.py tests/test_cli.py -k "intake_source"
```

Expected: FAIL because there is no source-intake module or CLI entrypoint yet.

## Task 2: Implement the source-intake adapter

**Files:**
- Create: `src/sentieon_assist/source_intake.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Implement the source-intake module**

Add:

- source-class validation
- supported file-type detection
- local file loading
- markdown rendering for imported source material
- metadata enrichment using the existing scaffold defaults

- [ ] **Step 2: Add the CLI command**

Support:

- `--source-class`
- `--source-path`
- `--kind`
- `--id`
- `--name`
- `--inbox-dir`
- `--file-stem`

- [ ] **Step 3: Run the targeted tests to verify they pass**

Run:

```bash
python3.11 -m pytest -q tests/test_source_intake.py tests/test_cli.py -k "intake_source"
```

Expected: PASS

## Task 3: Verify the subphase without widening scope

**Files:**
- Test: `tests/test_source_intake.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_docs_contract.py`

- [ ] **Step 1: Run focused verification**

Run:

```bash
python3.11 -m pytest -q tests/test_source_intake.py tests/test_cli.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 2: Confirm the boundary still holds**

Re-check that this phase does not add:

- active knowledge mutation
- runtime answering changes
- activation shortcuts
