# Sengent Knowledge Build Phase 5 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn parameter promotion into an operator-friendly workflow by emitting actionable suggestion artifacts, suppressing already-covered shared/global parameters, and making the build report point maintainers at only the real gaps.

**Architecture:** Keep Sengent's runtime route unchanged and continue treating `knowledge build` as an offline compiler. Phase 5 builds on the phase-4 parameter-promotion contract: extracted parameter candidates remain non-authoritative, structured metadata still owns promotion, but the compiler now classifies unmatched high-confidence parameters into review buckets, generates suggestion records for true gaps, and suppresses noise when the active packs already cover a parameter in the same module or shared `sentieon-cli` module.

**Tech Stack:** Python 3.11, existing `sentieon_assist` CLI package, `pytest`, local JSON/JSONL artifacts, YAML front matter and sidecar metadata

---

## Chunk 1: Review Workflow Plan

### Task 1: Add failing tests for actionable parameter review suggestions

**Files:**
- Modify: `tests/test_knowledge_build.py`
- Reference: `src/sentieon_assist/knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- build writes `parameter_review_suggestion.jsonl`
- true parameter gaps become actionable suggestion rows with:
  - `relative_path`
  - `module_id`
  - `parameter_name`
  - `suggested_action`
  - a structured metadata template
- report includes suggestion counts and points to the artifact path

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "parameter_review_suggestion or shared_parameter_coverage"`
Expected: FAIL because phase-4 build emits no suggestion artifact and does not suppress already-covered shared parameters

## Chunk 2: Shared-Parameter Noise Reduction

### Task 2: Classify unmatched candidates against active module/shared parameter coverage

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`
- Reference: `sentieon-note/sentieon-modules.json`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- if the active `sentieon-cli` module already covers a parameter such as `-t`, an extracted module-local `-t` candidate becomes `covered_by_shared_module`
- those covered parameters do not produce review suggestions
- same-module already-covered parameters can be bucketed separately from true gaps

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "shared_parameter_coverage or module_parameter_coverage"`
Expected: FAIL because phase-4 review flow treats all unmatched high-confidence candidates as review-needed gaps

- [ ] **Step 3: Implement conservative coverage classification**

In `src/sentieon_assist/knowledge_build.py`:
- build an active module-parameter index from `sentieon-modules.json`
- classify unmatched high-confidence extracted parameters as:
  - `candidate_only`
  - `covered_by_module`
  - `covered_by_shared_module`
- only `candidate_only` rows should remain actionable review gaps

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "shared_parameter_coverage or module_parameter_coverage"`
Expected: PASS

## Chunk 3: Suggestion Artifact And Report

### Task 3: Emit actionable metadata templates for true parameter gaps

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- `parameter_review_suggestion.jsonl` contains one row per true `candidate_only` gap
- each suggestion row carries a ready-to-fill metadata template with:
  - `name`
  - `aliases`
  - `summary`
  - `details`
  - `values`
- report includes counts for:
  - promoted parameters
  - review-needed candidate gaps
  - covered-by-shared-module items

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "parameter_review_suggestion or report_shared_coverage"`
Expected: FAIL because phase-4 report lacks suggestion and covered-shared counts

- [ ] **Step 3: Implement the operator-facing outputs**

In `src/sentieon_assist/knowledge_build.py`:
- add `ParameterReviewSuggestionRecord`
- emit `parameter_review_suggestion.jsonl`
- include the artifact path and review bucket counts in `report.md`
- keep the report maintainers-first: only true gaps should appear as action items

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "parameter_review_suggestion or report_shared_coverage"`
Expected: PASS

## Chunk 4: Full Verification And Docs

### Task 4: Verify phase 5 without regressing existing support or build gates

**Files:**
- Modify: `docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`
- Modify: `docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase5.md`
- Test: `tests/test_knowledge_build.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_pilot_readiness.py`
- Test: `tests/test_pilot_closed_loop.py`

- [ ] **Step 1: Run focused knowledge-build coverage**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py`
Expected: PASS

- [ ] **Step 2: Run focused pilot coverage**

Run: `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS

- [ ] **Step 4: Run pilot gates**

Run: `python3.11 scripts/pilot_readiness_eval.py`
Expected: PASS

Run: `python3.11 scripts/pilot_closed_loop.py`
Expected: PASS with stable risk output

- [ ] **Step 5: Update docs to reflect the operator workflow**

Reflect the phase-5 additions in the design doc:
- `parameter_review_suggestion.jsonl`
- coverage buckets for already-covered same-module/shared parameters
- report sections that isolate true gaps from already-covered noise
