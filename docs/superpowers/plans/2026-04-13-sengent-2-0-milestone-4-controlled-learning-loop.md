# Sengent 2.0 Milestone 4 Controlled Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn runtime `gap_record` output into a controlled learning entrypoint that creates inbox-ready incident artifacts, exposes them in `knowledge build` / `knowledge review`, and compiles them into the `incident-memory` candidate pack without mutating active runtime knowledge directly.

**Architecture:** Keep the current runtime answer path unchanged after capture. Phase 4 adds a narrow bridge from session-log gap records into the maintainer workflow: export selected gap turns into structured inbox artifacts, let `knowledge build` compile those artifacts into `incident-memory` candidate entries plus review artifacts, and keep activation behind the existing review/gate/activate flow.

**Tech Stack:** Python 3.11, pytest, existing `session_events` runtime logs, `knowledge_build` compiler, `incident_memory` pack loader, CLI knowledge subcommands

---

## Scope Boundary

This plan implements **Milestone 4 only** from the approved 2.0 spec.

This plan explicitly includes:

- session-log-driven export of runtime gap records into inbox artifacts
- a first-class incident/gap scaffold contract for the knowledge inbox
- compilation of incident gap artifacts into `incident-memory.json` candidate entries
- maintainer-visible build artifacts / report sections for captured gaps
- one end-to-end Sentieon closed-loop sample from gap capture to compiled candidate pack

This plan explicitly does **not** include:

- automatic activation of newly captured gaps
- direct runtime consumption changes beyond existing `incident_memory` loader
- model training or online learning
- onboarding a second vendor profile

## File Map

- Create: `src/sentieon_assist/gap_intake.py`
  - export selected `gap_record` values from session logs
  - derive deterministic inbox file names and metadata payloads
  - write inbox markdown + sidecar artifacts for controlled review
- Modify: `src/sentieon_assist/knowledge_build.py`
  - add incident scaffold defaults
  - accept incident metadata
  - compile `incident-memory` candidate entries
  - write a gap-intake review artifact and report section
- Modify: `src/sentieon_assist/cli.py`
  - add `knowledge intake-gap`
  - parse `--session-id`, `--turn-id`, `--latest`, `--runtime-root`, `--inbox-dir`
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
  - document runtime-gap intake flow
- Create: `tests/test_gap_intake.py`
  - focused export / inbox writer coverage
- Modify: `tests/test_cli.py`
  - CLI coverage for `knowledge intake-gap`
- Modify: `tests/test_knowledge_build.py`
  - incident artifact compilation / report coverage

## Chunk 1: Gap Intake Export Contract

### Task 1: Export session-log gap records into inbox incident artifacts

**Files:**
- Create: `src/sentieon_assist/gap_intake.py`
- Modify: `src/sentieon_assist/cli.py`
- Test: `tests/test_gap_intake.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing export tests**

Add tests that prove:

- a turn view with `gap_record` can be exported into a markdown + `.meta.yaml` pair
- the metadata carries `pack_target=incident-memory.json` and an incident entry type
- `--latest` picks the latest turn in a session that actually has a gap record
- explicit `--turn-id` rejects turns without a gap record
- file stems remain deterministic and collision-safe for repeated exports

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_intake.py tests/test_cli.py -k "intake_gap"
```

Expected: FAIL because there is no gap intake module or CLI entrypoint yet.

- [ ] **Step 3: Implement the gap export module**

In `src/sentieon_assist/gap_intake.py`, add:

- a small result type for created artifact paths
- helpers to load turn views from `session_events`
- a selector for `latest gap turn` vs explicit `turn_id`
- a deterministic file-stem builder using session / turn / gap type
- a markdown renderer that preserves:
  - original user question
  - known context
  - missing materials
  - capture timestamp
- a metadata renderer that maps runtime gaps into incident intake defaults

Keep this module free of direct build / activation logic.

- [ ] **Step 4: Add the CLI entrypoint**

In `src/sentieon_assist/cli.py`:

- extend `knowledge` help text with `intake-gap`
- add option parsing for:
  - `--session-id`
  - `--turn-id`
  - `--latest`
  - `--runtime-root`
  - `--inbox-dir`
- wire the subcommand to `gap_intake.py`
- print created artifact paths and selected turn metadata

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_intake.py tests/test_cli.py -k "intake_gap"
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/sentieon_assist/gap_intake.py src/sentieon_assist/cli.py tests/test_gap_intake.py tests/test_cli.py
git commit -m "feat: add gap intake export flow"
```

## Chunk 2: Incident Build And Review Visibility

### Task 2: Compile incident intake artifacts into candidate `incident-memory` entries and build review artifacts

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Write the failing build/report tests**

Add tests that prove:

- `knowledge scaffold --kind incident` produces an incident-memory-compatible template
- inbox incident metadata compiles into `candidate-packs/incident-memory.json`
- the compiled incident entry preserves gap-specific fields:
  - `gap_type`
  - `vendor_version`
  - `user_question`
  - `missing_materials`
  - `known_context`
  - `captured_at`
- build writes a dedicated review artifact for captured gaps
- `report.md` surfaces the count/path of captured gap records

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_knowledge_build.py -k "incident or gap_intake"
```

Expected: FAIL because incident scaffolds and incident compilation do not exist yet.

- [ ] **Step 3: Extend scaffold and compiler contracts**

In `src/sentieon_assist/knowledge_build.py`:

- add a new scaffold kind: `incident`
- map it to the vendor profile `incident-memory` runtime pack
- add metadata defaults for both manual and runtime-captured incident entries
- teach `_compile_candidate_entry()` how to emit `incident-memory` entries
- keep candidate compilation deterministic and append-only by `id`

- [ ] **Step 4: Add review/build visibility**

Still in `knowledge_build.py`:

- define a gap-intake review record type
- write `gap_intake_review.jsonl` into the build directory
- add a `Gap intake review` section to `report.md`
- ensure builds with incident intake remain `candidate_only` until explicit gate/activate

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run:

```bash
python3.11 -m pytest -q tests/test_knowledge_build.py -k "incident or gap_intake"
```

Expected: PASS

- [ ] **Step 6: Run compatibility regressions**

Run:

```bash
python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py tests/test_incident_memory.py
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/sentieon_assist/knowledge_build.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_cli.py
git commit -m "feat: compile gap intake into incident memory"
```

## Chunk 3: Operator Flow And End-To-End Verification

### Task 3: Document and verify the first controlled learning loop

**Files:**
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_knowledge_build.py`

- [ ] **Step 1: Update the operator manual**

Document:

- how to choose a session / turn with a gap record
- how to run `sengent knowledge intake-gap`
- how the generated incident artifact enters `knowledge build` / `knowledge review`
- that activate still requires gate and explicit operator intent

- [ ] **Step 2: Add one end-to-end CLI/build test**

Add a test that:

- creates a session log with a gap record
- runs `knowledge intake-gap`
- runs `knowledge build`
- verifies `incident-memory.json` candidate output contains the captured incident entry
- verifies the build report mentions the gap intake artifact

- [ ] **Step 3: Run the end-to-end slice**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py tests/test_knowledge_build.py -k "intake_gap_end_to_end or incident_build"
```

Expected: PASS

- [ ] **Step 4: Run Phase 4 verification suite**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_intake.py tests/test_cli.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_session_events.py
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md tests/test_cli.py tests/test_knowledge_build.py
git commit -m "docs: add controlled learning loop operator flow"
```

## Final Verification

After all chunks are complete, run:

```bash
python3.11 -m pytest -q tests/test_gap_intake.py tests/test_cli.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_session_events.py tests/test_answering.py tests/test_support_coordinator.py
```

Expected: PASS

If the suite is too slow, split only after confirming the full target list is covered and report each exact command/result.
