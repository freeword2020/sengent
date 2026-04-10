# Sengent Knowledge Build Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add low-risk script and parameter candidate extraction to the local knowledge build pipeline so maintainers can drop reference docs and shell snippets into the inbox while the system emits structured candidate artifacts, conservative module-pack enrichments, and exception-first review outputs.

**Architecture:** Keep the runtime support path unchanged: active `sentieon-note/*.json` packs still drive answering, and knowledge build remains an offline compiler pipeline. Phase 3 extends the compiler side only: it extracts script blocks and parameter candidates from markdown/shell sources, emits dedicated JSONL artifacts, conservatively folds high-confidence results into module candidate packs, and pushes ambiguous cases into reportable exception queues instead of silently guessing.

**Tech Stack:** Python 3.11, existing `sentieon_assist` CLI package, `pytest`, local JSON/JSONL artifacts, YAML metadata, regex-based command parsing

---

## Chunk 1: Candidate Artifact Schema

### Task 1: Add failing tests and schema for script/parameter candidate artifacts

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`
- Reference: `docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- every build can write `script_candidate_record.jsonl`
- every build can write `parameter_candidate_record.jsonl`
- markdown code fences and shell files generate script candidate records with:
  - `doc_id`
  - `relative_path`
  - `module_hint`
  - `command_lines`
  - `confidence`
- extracted options generate parameter candidate records with:
  - `parameter_name`
  - `module_hint`
  - `source_relative_path`
  - `script_candidate_id`

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "script_candidate_record or parameter_candidate_record"`
Expected: FAIL because phase-2 build writes no candidate extraction artifacts

- [ ] **Step 3: Implement the minimal artifact schema**

In `src/sentieon_assist/knowledge_build.py`:
- add dataclasses for `ScriptCandidateRecord` and `ParameterCandidateRecord`
- thread candidate collections through `run_knowledge_build()`
- emit:
  - `runtime/knowledge-build/<build_id>/script_candidate_record.jsonl`
  - `runtime/knowledge-build/<build_id>/parameter_candidate_record.jsonl`

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "script_candidate_record or parameter_candidate_record"`
Expected: PASS

## Chunk 2: Extraction Heuristics

### Task 2: Extract high-confidence script blocks and module hints from markdown and shell docs

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- fenced bash/sh/shell blocks in markdown become script candidates
- raw `.sh/.bash/.zsh` inbox files become script candidates
- module inference works for:
  - `sentieon-cli dnascope`
  - `sentieon-cli dnascope-longread`
  - `sentieon driver --algo GVCFtyper`
- docs with no confident module mapping still emit script candidates but are marked `confidence=low`

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "script_candidates_from_markdown or script_candidates_from_shell or module_hint"`
Expected: FAIL because extraction heuristics do not exist yet

- [ ] **Step 3: Implement the minimal extraction**

In `src/sentieon_assist/knowledge_build.py`:
- extract fenced script blocks from markdown
- normalize shell-like sources into command-line candidates
- infer module hints conservatively from:
  - explicit metadata such as `module_id`
  - `sentieon-cli <subcommand>`
  - `sentieon driver --algo <algo>`
- tag unresolved cases with low confidence instead of inventing a module

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "script_candidates_from_markdown or script_candidates_from_shell or module_hint"`
Expected: PASS

## Chunk 3: Parameter Candidate Extraction

### Task 3: Extract parameter candidates from script candidates without changing runtime packs yet

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- long options such as `--pcr_free`, `--tech`, `--haploid_bed` become parameter candidates
- short options such as `-r`, `-t`, `-d` become parameter candidates
- duplicate parameter mentions within the same script candidate are deduplicated
- candidates without a confident module hint are still emitted but flagged as low-confidence or queued for review

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "parameter_candidates or deduplicate_parameter_mentions"`
Expected: FAIL because parameter extraction is not implemented

- [ ] **Step 3: Implement the minimal parameter extraction**

In `src/sentieon_assist/knowledge_build.py`:
- parse long and short options from script candidate command lines
- deduplicate parameter names per script candidate
- preserve `module_hint` and confidence on each parameter candidate
- avoid pretending that every extracted option is production-ready runtime knowledge

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "parameter_candidates or deduplicate_parameter_mentions"`
Expected: PASS

## Chunk 4: Conservative Candidate-Pack Enrichment

### Task 4: Fold high-confidence script candidates into module candidate packs only when ownership is clear

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`
- Reference: `sentieon-note/sentieon-modules.json`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- a module-targeted markdown doc with a valid script block enriches its candidate module entry with:
  - `script_examples`
- enrichment only happens when the module id is explicit or high-confidence
- parameter candidates remain review artifacts rather than silently mutating runtime-oriented module pack fields
- low-confidence script/parameter candidates stay in artifacts and report queues, but do not silently mutate candidate module packs

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "module_candidate_enrichment or low_confidence_not_compiled"`
Expected: FAIL because extracted candidates are not yet folded into module candidate packs

- [ ] **Step 3: Implement the minimal conservative enrichment**

In `src/sentieon_assist/knowledge_build.py`:
- attach high-confidence script candidates to module entries as `script_examples`
- keep merge rules conservative:
  - same-doc ownership only
  - explicit or high-confidence module mapping only
  - parameter candidates remain review-only unless a later phase introduces a stricter promotion contract
  - low-confidence candidates remain review-only

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "module_candidate_enrichment or low_confidence_not_compiled"`
Expected: PASS

## Chunk 5: Exception-First Review Output

### Task 5: Surface extraction ambiguities in the report instead of forcing maintainers to inspect raw artifacts

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- report includes:
  - script candidate count
  - parameter candidate count
  - extraction ambiguities section
- ambiguous module inference appears in `exceptions.jsonl` or a clearly named extraction exception queue
- report points maintainers to the exact file that needs human review

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "extraction_ambiguity or candidate_counts_in_report"`
Expected: FAIL because phase-2 reporting does not cover extraction-specific review

- [ ] **Step 3: Implement the minimal report upgrade**

In `src/sentieon_assist/knowledge_build.py`:
- emit extraction ambiguity exceptions for low-confidence module ownership
- add candidate extraction counts to `report.md`
- keep the report maintainers-first:
  - ambiguity queue before raw counts
  - exact file paths before implementation detail

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "extraction_ambiguity or candidate_counts_in_report"`
Expected: PASS

## Chunk 6: Full Verification

### Task 6: Verify phase 3 without regressing the current support and build lifecycle

**Files:**
- Modify: `docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase3.md`
- Modify: `docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`
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

- [ ] **Step 4: Update docs if implementation introduces new artifact/report names**

Reflect the final phase-3 additions in the design doc, especially:
- script candidate artifacts
- parameter candidate artifacts
- extraction ambiguity queue
- conservative module enrichment rules

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase3.md docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md src/sentieon_assist/knowledge_build.py tests/test_knowledge_build.py tests/test_cli.py tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py
git commit -m "feat: add script and parameter candidate extraction to knowledge build"
```
