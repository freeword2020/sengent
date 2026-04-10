# Sengent Knowledge Build Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the first maintainable end-to-end knowledge build workflow by reducing maintainer metadata burden, expanding candidate-pack compilation, and adding candidate-only gate and activation flows.

**Architecture:** Keep runtime support behavior unchanged: active `sentieon-note/*.json` packs still power the assistant, while `knowledge build` produces candidate packs under `runtime/knowledge-build/<build_id>/`. Phase 2 adds low-friction metadata intake, broader compiler coverage, maintainer-facing diff/report artifacts, and a gate/activate path that evaluates candidate packs before promotion into the active source directory.

**Tech Stack:** Python 3.11, existing `sentieon_assist` CLI package, `pytest`, local JSON/JSONL artifacts, optional `docling`, YAML metadata

---

## Chunk 1: Maintainer Metadata Intake

### Task 1: Add sidecar metadata intake so maintainers do not need to edit raw docs

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`
- Reference: `docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- markdown front matter still works
- a sibling metadata file such as `fastdedup.meta.yaml` can provide the same fields without modifying the raw doc
- sidecar metadata overrides missing fields but does not silently replace explicit front matter values
- build report surfaces `metadata_missing` only for fields still absent after merge

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "sidecar or metadata_missing"`
Expected: FAIL because sidecar metadata intake does not exist yet

- [ ] **Step 3: Implement the minimal metadata merge**

In `src/sentieon_assist/knowledge_build.py`:
- add sidecar metadata discovery for `*.meta.yaml` and `*.meta.yml`
- merge sidecar metadata after parser extraction
- keep merge rules explicit:
  - parser/front matter remains authoritative for fields it already sets
  - sidecar fills gaps
  - unresolved fields stay in `metadata_missing`
- record merged metadata into `CanonicalDocumentRecord.source_metadata`

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "sidecar or metadata_missing"`
Expected: PASS

## Chunk 2: Compiler Coverage Expansion

### Task 2: Expand candidate-pack compilation beyond modules and workflows

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`
- Reference: `sentieon-note/external-format-guides.json`
- Reference: `sentieon-note/external-tool-guides.json`
- Reference: `sentieon-note/external-error-associations.json`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- metadata-tagged inbox docs can compile candidate entries into:
  - `external-format-guides.json`
  - `external-tool-guides.json`
  - `external-error-associations.json`
- duplicate candidate ids are queued as build exceptions instead of silently winning
- unsupported `pack_target` or `entry_type` values appear in compile skips

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "external_format or external_tool or external_error or duplicate_candidate"`
Expected: FAIL because compiler support is still limited to modules and workflows

- [ ] **Step 3: Implement the minimal compiler expansion**

In `src/sentieon_assist/knowledge_build.py`:
- extend `_compile_candidate_entry()` for external format/tool/error entry shapes
- add duplicate-id detection inside the build, not just within existing active packs
- queue duplicate/conflicting candidates into `exceptions.jsonl`
- keep the compiler conservative: only compile when required metadata is present

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "external_format or external_tool or external_error or duplicate_candidate"`
Expected: PASS

## Chunk 3: Maintainer Report And Build Diff

### Task 3: Make the report exception-first and change-focused for low-coding maintainers

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- report lists changed candidate packs and changed entry ids
- report separates:
  - parse exceptions
  - metadata missing
  - compile skips
  - duplicate/conflict exceptions
- manifest records a machine-readable diff summary:
  - added ids
  - updated ids
  - unchanged pack files

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "report_diff or changed_ids or duplicate_exception"`
Expected: FAIL because the report is still mostly count-based

- [ ] **Step 3: Implement the minimal report and diff summary**

In `src/sentieon_assist/knowledge_build.py`:
- compute per-pack diff summaries by comparing active and candidate pack ids
- write diff details into `candidate-packs/manifest.json`
- surface only changed ids and exception queues in `report.md`
- keep the report maintainers-first:
  - exceptions before counts
  - changed packs before raw artifact paths

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py -k "report_diff or changed_ids or duplicate_exception"`
Expected: PASS

## Chunk 4: Candidate-Source Gates

### Task 4: Let pilot gates evaluate candidate packs instead of only active packs

**Files:**
- Modify: `src/sentieon_assist/pilot_readiness.py`
- Modify: `src/sentieon_assist/pilot_closed_loop.py`
- Modify: `scripts/pilot_readiness_eval.py`
- Modify: `scripts/pilot_closed_loop.py`
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_pilot_readiness.py`
- Modify: `tests/test_pilot_closed_loop.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- `run_pilot_readiness_evaluation()` accepts an explicit `source_directory`
- `run_pilot_closed_loop()` accepts an explicit `source_directory`
- script entrypoints accept `--source-dir`
- `knowledge build` report points at candidate-pack-aware gate commands

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py tests/test_knowledge_build.py -k "source_dir or candidate_gate"`
Expected: FAIL because pilot code still hardcodes `sentieon-note/`

- [ ] **Step 3: Implement candidate-source-aware evaluation**

In the pilot modules and scripts:
- thread optional `source_directory` through readiness and closed-loop evaluators
- default to `repo_root / "sentieon-note"` for backward compatibility
- update `knowledge build` report so its recommended commands target `candidate-packs/`

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py tests/test_knowledge_build.py -k "source_dir or candidate_gate"`
Expected: PASS

## Chunk 5: Activation Flow

### Task 5: Add an explicit activation command that promotes a candidate build only after passing gates

**Files:**
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- `knowledge activate --build-id <id>` resolves the build directory under the configured build root
- activation copies candidate packs into the active source directory only when a gate report file says the candidate build passed
- activation records an activation manifest or stamp under the build directory
- activation refuses to proceed when the candidate build is missing, incomplete, or marked failed

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_cli.py tests/test_knowledge_build.py -k "knowledge_activate or activation_manifest"`
Expected: FAIL because activation flow does not exist yet

- [ ] **Step 3: Implement the minimal gated activation**

In `src/sentieon_assist/knowledge_build.py` and `src/sentieon_assist/cli.py`:
- add activation helpers that locate a build, verify required artifacts, and copy candidate pack JSON files into the active source directory
- require a gate-status artifact written by the candidate-source evaluation step
- write an activation manifest with:
  - build id
  - activation timestamp
  - activated files
  - gate summary

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_cli.py tests/test_knowledge_build.py -k "knowledge_activate or activation_manifest"`
Expected: PASS

## Chunk 6: Full Verification And Maintainer Workflow Check

### Task 6: Verify the phase-2 workflow end-to-end

**Files:**
- Modify: `docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`
- Modify: `docs/superpowers/plans/2026-04-09-sengent-knowledge-build-phase2.md`
- Test: `tests/test_knowledge_build.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_pilot_readiness.py`
- Test: `tests/test_pilot_closed_loop.py`

- [ ] **Step 1: Run focused knowledge-build coverage**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py`
Expected: PASS

- [ ] **Step 2: Run focused pilot regression coverage**

Run: `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS

- [ ] **Step 4: Run candidate-pack-aware pilot readiness gate**

Run: `python3.11 scripts/pilot_readiness_eval.py --source-dir runtime/knowledge-build/<build_id>/candidate-packs`
Expected: All gates pass

- [ ] **Step 5: Run candidate-pack-aware pilot closed loop**

Run: `python3.11 scripts/pilot_closed_loop.py --source-dir runtime/knowledge-build/<build_id>/candidate-packs`
Expected: `Quality score: 100`, `Risk level: stable`

- [ ] **Step 6: Run activation only after gates pass**

Run: `PYTHONPATH=src python3.11 -m sentieon_assist --source-dir sentieon-note knowledge activate --build-root runtime/knowledge-build --build-id <build_id>`
Expected: candidate packs are promoted into the active source directory and activation manifest is written

- [ ] **Step 7: Update docs to reflect the operator workflow**

Update the design/spec if implementation details changed, especially:
- sidecar metadata intake
- candidate-source gate commands
- activation contract

- [ ] **Step 8: Commit**

```bash
git add docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md docs/superpowers/plans/2026-04-09-sengent-knowledge-build-phase2.md src/sentieon_assist/cli.py src/sentieon_assist/knowledge_build.py src/sentieon_assist/pilot_readiness.py src/sentieon_assist/pilot_closed_loop.py scripts/pilot_readiness_eval.py scripts/pilot_closed_loop.py tests/test_knowledge_build.py tests/test_cli.py tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py
git commit -m "feat: complete candidate-pack knowledge build workflow"
```
