# Factory Draft Review Integration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach `factory_model_draft` artifacts to a build so maintainers can discover them through `knowledge queue`, inspect them through CLI review surfaces, and keep them strictly review-only.

**Architecture:** Extend the existing offline factory draft interface with optional build attachment. Attached drafts write into a canonical `factory-drafts/` directory under a reviewed build, `knowledge_review.py` aggregates them into a new maintainer queue bucket, and CLI adds a read-only `knowledge review-factory-draft` surface for build-level and per-draft inspection.

**Tech Stack:** Python 3.11, pytest, existing knowledge build/review CLI, local JSON artifacts, markdown operator docs

---

## File Map

- Modify: `src/sentieon_assist/factory_model.py`
  - build attachment contract
  - canonical output resolution
  - draft discovery / loading helpers
  - inspect view formatting
- Modify: `src/sentieon_assist/knowledge_review.py`
  - queue aggregation for attached factory drafts
  - bucket summary text
- Modify: `src/sentieon_assist/cli.py`
  - parse `factory-draft` build options
  - add `review-factory-draft` subcommand
  - expose new help text
- Modify: `tests/test_factory_model.py`
  - build attachment contract tests
  - inspect formatting tests
- Modify: `tests/test_knowledge_review.py`
  - queue bucket coverage for factory drafts
- Modify: `tests/test_cli.py`
  - attached draft creation
  - queue output
  - review-factory-draft output
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
  - operator workflow for attached factory drafts

## Chunk 1: Define Build-Attached Draft Behavior

### Task 1: Write failing tests for the integration contract

**Files:**
- Modify: `tests/test_factory_model.py`
- Modify: `tests/test_knowledge_review.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add factory model tests for build attachment**

Cover:

- attached drafts can resolve to `<build_dir>/factory-drafts/`
- artifact retains build-scoped review metadata
- standalone drafts remain possible and stay non-queue by default

- [ ] **Step 2: Add queue aggregation tests**

Cover:

- attached `factory_model_draft` artifacts add a `pending-factory-draft-review` bucket
- bucket samples show draft id / task kind
- bucket next action and recommended command point to CLI review flow

- [ ] **Step 3: Add CLI tests**

Cover:

- `knowledge factory-draft --build-id <id>` writes a canonical attached artifact
- `knowledge review-factory-draft --build-id <id>` prints draft summaries without opening JSON manually
- `knowledge review-factory-draft --build-id <id> --draft-id <id>` prints single-draft details

- [ ] **Step 4: Run focused tests to confirm failure**

Run:

```bash
python3.11 -m pytest -q tests/test_factory_model.py tests/test_knowledge_review.py tests/test_cli.py -k "factory_draft or review_factory_draft or maintainer_queue"
```

Expected: FAIL because build-attached draft review integration does not exist yet.

## Chunk 2: Implement Canonical Draft Attachment And Inspect Surface

### Task 2: Extend the factory draft module and CLI

**Files:**
- Modify: `src/sentieon_assist/factory_model.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Add build attachment resolution**

Implement:

- canonical draft directory naming
- build existence validation
- optional `--build-id` / `--build-root`
- result metadata that tells whether the artifact is attached to a build

- [ ] **Step 2: Add draft discovery and loading helpers**

Implement:

- list attached drafts for a build
- load by `draft_id`
- filter invalid or unrelated JSON safely

- [ ] **Step 3: Add inspect formatting**

Implement:

- build-level summary formatter
- single-draft detail formatter
- review guidance text with why / next action / recommended command

- [ ] **Step 4: Wire CLI**

Implement:

- `knowledge factory-draft --build-id [--build-root]`
- `knowledge review-factory-draft [--build-id] [--build-root] [--draft-id]`
- help text and validation

- [ ] **Step 5: Run focused tests to verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_factory_model.py tests/test_knowledge_review.py tests/test_cli.py -k "factory_draft or review_factory_draft or maintainer_queue"
```

Expected: PASS

## Chunk 3: Queue Integration And Operator Guidance

### Task 3: Connect attached drafts to maintainer next actions

**Files:**
- Modify: `src/sentieon_assist/knowledge_review.py`
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`

- [ ] **Step 1: Add the new queue bucket**

Implement:

- `pending-factory-draft-review`
- why it matters text
- next action text
- recommended command pointing to `knowledge review-factory-draft`

- [ ] **Step 2: Update operator manual**

Document:

- how to create an attached factory draft for a build
- how queue surfaces it
- how to inspect it
- reminder that reviewed content must still flow through inbox/build/gate/activate

- [ ] **Step 3: Run docs-adjacent verification**

Run:

```bash
python3.11 -m pytest -q tests/test_factory_model.py tests/test_knowledge_review.py tests/test_cli.py tests/test_docs_contract.py
```

Expected: PASS

## Chunk 4: Fresh Regression Verification And Commit

### Task 4: Verify the whole requested baseline and commit intentionally

**Files:**
- Verify only

- [ ] **Step 1: Run the requested fresh suite**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_gap_intake.py tests/test_source_intake.py tests/test_dataset_export.py tests/test_factory_model.py tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py tests/test_answering.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_pilot_closed_loop.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 2: Review the diff for boundary compliance**

Confirm:

- no runtime truth path change
- no candidate/active auto-promotion
- no remote provider logic

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-13-sengent-2-0-factory-draft-review-integration-design.md docs/superpowers/plans/2026-04-13-sengent-2-0-factory-draft-review-integration.md docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md src/sentieon_assist/factory_model.py src/sentieon_assist/knowledge_review.py src/sentieon_assist/cli.py tests/test_factory_model.py tests/test_knowledge_review.py tests/test_cli.py
git commit -m "feat: integrate factory drafts into review flow"
```
