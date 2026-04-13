# Sengent 2.0 Maintainer Experience Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a CLI-first maintainer queue so maintainers can see actionable review buckets and next-step commands for a build without manually stitching together raw artifacts.

**Architecture:** Keep `knowledge review` as the raw evidence surface and add a thin aggregation layer on top. The new `knowledge queue` command reads build artifacts already produced by `knowledge build`, derives queue buckets plus next actions, and never mutates the build, runtime, or active packs.

**Tech Stack:** Python 3.11, pytest, existing build artifacts in `runtime/knowledge-build/<build_id>`, current CLI package, local JSON/JSONL reports

---

## Scope Boundary

This phase implements the first complete chunk of the roadmap’s maintainer convenience refactor.

This phase explicitly includes:

- a `knowledge queue` maintainer view
- bucket aggregation for:
  - pending gap triage
  - pending source review
  - pending parameter review
  - pending gate input
  - candidate pack changes
- CLI help and output wiring
- focused tests and verification

This phase explicitly does **not** include:

- automatic triage or gate execution
- UI frontend work
- contradiction scan
- activation behavior changes

## File Map

- Create: `src/sentieon_assist/knowledge_review.py`
  - load build artifacts
  - derive maintainer queue buckets
  - format actionable queue summaries
- Modify: `src/sentieon_assist/cli.py`
  - add `knowledge queue`
  - parse `--build-id` / `--build-root`
  - print queue summary
- Modify: `src/sentieon_assist/knowledge_build.py`
  - optionally extend `KnowledgeReviewResult` only if needed for shared build lookup
- Create: `tests/test_knowledge_review.py`
  - bucket derivation and formatting coverage
- Modify: `tests/test_cli.py`
  - CLI queue coverage
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
  - document when to use `knowledge queue`

## Chunk 1: Queue Aggregation Contract

### Task 1: Lock the queue model with failing tests

**Files:**
- Create: `tests/test_knowledge_review.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Add tests that prove:

- queue loads the latest or selected build
- queue emits buckets for:
  - pending gap triage
  - pending source review
  - pending parameter review
  - pending gate input
  - candidate pack changes
- each bucket carries:
  - count
  - why it matters
  - next action
  - recommended command
  - artifact path
- CLI `knowledge queue` prints a concise summary with bucket headings

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_knowledge_review.py tests/test_cli.py -k "knowledge_queue"
```

Expected: FAIL because there is no queue aggregation module or CLI command yet.

## Chunk 2: Implement Queue MVP

### Task 2: Add queue aggregation and CLI wiring

**Files:**
- Create: `src/sentieon_assist/knowledge_review.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Implement artifact loaders**

Load:

- `candidate-packs/manifest.json`
- `parameter_review_suggestion.jsonl`
- `gap_intake_review.jsonl`
- `gap_eval_seed.jsonl`
- gate reports when present

- [ ] **Step 2: Implement queue bucket derivation**

Derive:

- `pending-gap-triage`
- `pending-source-review`
- `pending-parameter-review`
- `pending-gate-input`
- `candidate-pack-change`

- [ ] **Step 3: Implement formatter**

Output:

- build summary
- total pending queue count
- one section per non-empty bucket
- clear next-step command text

- [ ] **Step 4: Add CLI command**

Support:

- `sengent knowledge queue`
- `sengent knowledge queue --build-id <id>`
- `sengent knowledge queue --build-root <dir>`

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run:

```bash
python3.11 -m pytest -q tests/test_knowledge_review.py tests/test_cli.py -k "knowledge_queue"
```

Expected: PASS

## Chunk 3: Operator Flow And Verification

### Task 3: Document queue usage and verify against the current maintainer loop

**Files:**
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
- Test: `tests/test_knowledge_review.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_docs_contract.py`

- [ ] **Step 1: Update operator docs**

Document:

- `knowledge queue` as the first maintainer command after `knowledge build`
- `knowledge review` as the deeper evidence command
- how queue buckets map to next actions

- [ ] **Step 2: Run focused verification**

Run:

```bash
python3.11 -m pytest -q tests/test_knowledge_review.py tests/test_cli.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 3: Run broader regression verification**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_gap_intake.py tests/test_source_intake.py tests/test_cli.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_pilot_closed_loop.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-13-sengent-2-0-maintainer-experience-design.md docs/superpowers/plans/2026-04-13-sengent-2-0-maintainer-experience.md docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md src/sentieon_assist/knowledge_review.py src/sentieon_assist/cli.py tests/test_knowledge_review.py tests/test_cli.py
git commit -m "feat: add maintainer knowledge queue"
```
