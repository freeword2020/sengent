# Sengent 2.0 Factory Model Interface Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first offline factory model interface chunk so `Knowledge Factory` can produce audited review-needed draft artifacts through a provider-agnostic interface and a deterministic stub adapter.

**Architecture:** Keep the factory model layer completely offline and downstream. Add a provider-agnostic request/adapter/artifact contract, a stub adapter that generates deterministic draft payloads, and a CLI `knowledge factory-draft` surface that writes JSON draft artifacts without touching runtime facts or active packs.

**Tech Stack:** Python 3.11, pytest, local JSON artifacts, existing CLI command structure, current knowledge factory modules

---

## Scope Boundary

This phase implements the first complete chunk of the roadmap’s large-model factory interface work.

This phase explicitly includes:

- provider-agnostic factory draft contracts
- supported task kind normalization
- stub adapter
- draft artifact writer
- CLI `knowledge factory-draft`
- auditability fields and operator guidance

This phase explicitly does **not** include:

- remote model providers
- runtime model usage
- automatic inbox/build mutation
- automatic activation
- deep task-specific extraction logic

## File Map

- Create: `src/sentieon_assist/factory_model.py`
  - request / template / artifact contracts
  - adapter protocol
  - stub adapter
  - draft artifact execution and summary formatting
- Modify: `src/sentieon_assist/cli.py`
  - add `knowledge factory-draft`
  - parse task / source refs / output / adapter / vendor / instruction
  - print draft summary
- Create: `tests/test_factory_model.py`
  - request normalization and artifact contract coverage
- Modify: `tests/test_cli.py`
  - CLI draft flow coverage
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
  - document that factory drafts are review-needed and non-active

## Chunk 1: Lock The Draft Artifact Contract

### Task 1: Write failing tests for factory draft behavior

**Files:**
- Create: `tests/test_factory_model.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add contract tests**

Add tests that prove:

- supported task kinds normalize correctly
- stub adapter writes a JSON artifact with:
  - `draft_id`
  - `task_kind`
  - `vendor_id`
  - `adapter`
  - `review_status`
  - `prompt_provenance`
  - `source_references`
  - `draft_payload`
- artifact is always marked `needs_review`

- [ ] **Step 2: Add CLI tests**

Add tests that prove:

- `sengent knowledge factory-draft --task ... --source-ref ... --output ...` writes an artifact
- repeated `--source-ref` values are preserved
- CLI summary reports output path, task kind, adapter id, review status, and source reference count

- [ ] **Step 3: Run targeted tests to confirm failure**

Run:

```bash
python3.11 -m pytest -q tests/test_factory_model.py tests/test_cli.py -k "factory_model or factory_draft"
```

Expected: FAIL because the factory model interface and CLI command do not exist yet.

## Chunk 2: Implement Stubbed Factory Model Interface

### Task 2: Add contracts, stub adapter, and CLI wiring

**Files:**
- Create: `src/sentieon_assist/factory_model.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Implement the request and template contracts**

Define:

- supported task kinds
- source reference normalization
- prompt template provenance
- adapter provenance

- [ ] **Step 2: Implement the stub adapter**

Make the stub adapter:

- deterministic
- explicit about being stub/local
- always emit review-needed payloads

- [ ] **Step 3: Implement draft artifact execution**

Read source refs, render prompt provenance, run the adapter, and write one JSON artifact containing:

- identity
- adapter provenance
- review status
- prompt provenance
- source references
- draft payload

- [ ] **Step 4: Add CLI command**

Support:

- `sengent knowledge factory-draft --task <task> --source-ref <path> --output <path>`
- optional `--vendor-id <id>`
- optional `--instruction <text>`
- optional `--adapter stub`

- [ ] **Step 5: Run targeted tests to verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_factory_model.py tests/test_cli.py -k "factory_model or factory_draft"
```

Expected: PASS

## Chunk 3: Operator Surface And Verification

### Task 3: Document the boundary and run fresh verification

**Files:**
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
- Verify: `tests/test_factory_model.py`
- Verify: `tests/test_cli.py`
- Verify: `tests/test_dataset_export.py`
- Verify: `tests/test_docs_contract.py`

- [ ] **Step 1: Update operator guidance**

Document:

- `knowledge factory-draft` is optional factory assistance
- output is review-needed only
- draft artifacts do not enter active packs automatically

- [ ] **Step 2: Run focused verification**

Run:

```bash
python3.11 -m pytest -q tests/test_factory_model.py tests/test_cli.py tests/test_dataset_export.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 3: Run broader regression verification**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_gap_intake.py tests/test_source_intake.py tests/test_dataset_export.py tests/test_factory_model.py tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py tests/test_answering.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_pilot_closed_loop.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-13-sengent-2-0-factory-model-interface-design.md docs/superpowers/plans/2026-04-13-sengent-2-0-factory-model-interface.md docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md src/sentieon_assist/factory_model.py src/sentieon_assist/cli.py tests/test_factory_model.py tests/test_cli.py
git commit -m "feat: add factory draft interface"
```
