# Sengent Knowledge Build Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic parameter-promotion contract to the offline knowledge build pipeline so maintainers can define reviewed module parameters in source metadata while extracted parameter candidates remain review inputs rather than silently becoming runtime knowledge.

**Architecture:** Keep Sengent's runtime path unchanged: active `sentieon-note/*.json` packs still drive support routing and answering, and `knowledge build` remains an offline compiler pipeline. Phase 4 extends the compiler side only: module docs may now carry structured `parameters` metadata that compiles into candidate module packs, while the build emits a machine-readable parameter review artifact and maintainer-first report sections that distinguish promoted parameters from extracted-but-unpromoted candidates.

**Tech Stack:** Python 3.11, existing `sentieon_assist` CLI package, `pytest`, local JSON/JSONL artifacts, YAML front matter and sidecar metadata, regex-based candidate extraction

---

## Chunk 1: Parameter Promotion Contract

### Task 1: Add failing tests for structured parameter promotion and review outputs

**Files:**
- Modify: `tests/test_knowledge_build.py`
- Reference: `src/sentieon_assist/knowledge_build.py`
- Reference: `sentieon-note/sentieon-modules.json`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- module docs with structured `parameters` metadata compile those entries into `candidate-packs/sentieon-modules.json`
- sidecar metadata can define module `parameters` without editing raw docs
- promotion keeps existing pack-style fields:
  - `name`
  - `aliases`
  - `summary`
  - `details`
  - `values`
- build emits a new machine-readable parameter review artifact that records:
  - promoted parameters
  - extracted high-confidence parameters that still lack structured promotion
- malformed or duplicate parameter definitions do not silently compile

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "parameter_promotion or parameter_review"`
Expected: FAIL because phase-3 build does not compile structured parameters or emit a review artifact

## Chunk 2: Candidate Module Parameter Compilation

### Task 2: Compile structured module parameters from front matter and sidecar metadata

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- structured `parameters` on module docs compile into candidate module entries
- sidecar metadata can supply `parameters` when the raw markdown stays untouched
- parameter normalization is conservative:
  - missing `name` or `summary` is rejected
  - `aliases`, `details`, and `values` become stable string lists
  - duplicate parameter names are queued as exceptions instead of silently overwriting

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "compile_module_parameters or sidecar_parameters or duplicate_parameter_definition"`
Expected: FAIL because candidate module compilation currently ignores `parameters`

- [ ] **Step 3: Implement the minimal compilation contract**

In `src/sentieon_assist/knowledge_build.py`:
- add a focused helper that compiles structured module `parameters`
- only allow this path for `sentieon-modules.json` module entries
- require explicit human-authored metadata for promotion; extracted parameter candidates remain non-authoritative
- queue malformed or duplicate definitions as exceptions

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "compile_module_parameters or sidecar_parameters or duplicate_parameter_definition"`
Expected: PASS

## Chunk 3: Parameter Review Artifact And Report

### Task 3: Emit parameter review records and maintainer-first review sections

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- build writes `parameter_promotion_review.jsonl`
- a module doc that both defines structured parameters and contains a matching script records:
  - promoted parameter rows
  - candidate-only rows for extracted high-confidence parameters that were not promoted
- report includes:
  - promoted parameter count
  - extracted-but-unpromoted parameter count
  - exact file paths for review-needed items
- low-confidence or ownership-ambiguous parameter candidates do not become promotion suggestions

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "parameter_promotion_review or unpromoted_parameter_report"`
Expected: FAIL because phase-3 build writes no promotion review artifact and report has no parameter-review section

- [ ] **Step 3: Implement the minimal review flow**

In `src/sentieon_assist/knowledge_build.py`:
- add a `ParameterPromotionReviewRecord` dataclass
- emit `parameter_promotion_review.jsonl`
- generate review records conservatively:
  - `promoted` for structured parameters
  - `candidate_only` for high-confidence extracted parameters from the same doc/module that still lack structured promotion
- keep low-confidence candidates out of promotion review noise
- surface summary counts and review-needed file paths in `report.md`

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "parameter_promotion_review or unpromoted_parameter_report"`
Expected: PASS

## Chunk 4: Full Verification And Docs

### Task 4: Verify phase 4 without regressing support or build activation flows

**Files:**
- Modify: `docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`
- Modify: `docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase4.md`
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

- [ ] **Step 4: Run candidate-source gates**

Run: `python3.11 scripts/pilot_readiness_eval.py`
Expected: PASS

Run: `python3.11 scripts/pilot_closed_loop.py`
Expected: PASS with stable risk output

- [ ] **Step 5: Update docs to reflect the final contract**

Reflect the phase-4 additions in the design doc:
- structured module parameter promotion via metadata
- `parameter_promotion_review.jsonl`
- report sections for promoted vs extracted-but-unpromoted parameters
- continued rule that raw extracted candidates do not directly become runtime knowledge
