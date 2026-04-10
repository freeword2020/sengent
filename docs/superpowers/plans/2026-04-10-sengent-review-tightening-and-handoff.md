# Sengent Review Tightening And Handoff Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adversarially review the full renew chain from P0 knowledge-build scaffolding through candidate packs, review/activate, and the latest rollback safety work, tighten architecture and behavior based on findings, commit the result, and deliver operator-facing architecture and maintenance documentation.

**Architecture:** Treat the entire renew pipeline as the review target: local ingest, canonical parse, candidate pack compiler, report/review workflow, candidate-aware eval gate, activation, and rollback. Use a separate review thread to inspect the uncommitted implementation from three angles: architecture robustness, functional completeness, and code quality. Feed accepted findings back into the existing offline build pipeline, keep `rule-first + structured packs + eval-gated activation`, then produce a stable handoff package.

**Tech Stack:** Python 3.11, pytest, existing CLI/runtime in `src/sentieon_assist`, Markdown docs under `docs/superpowers`

---

## Chunk 1: Review Intake

### Task 1: Capture full renew-chain scope and dispatch adversarial review

**Files:**
- Create: `/Users/zhuge/Documents/codex/harness/docs/superpowers/plans/2026-04-10-sengent-review-tightening-and-handoff.md`
- Review target: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/knowledge_build.py`
- Review target: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/cli.py`
- Review target: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/pilot_readiness.py`
- Review target: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/pilot_closed_loop.py`
- Review target: `/Users/zhuge/Documents/codex/harness/scripts/pilot_readiness_eval.py`
- Review target: `/Users/zhuge/Documents/codex/harness/scripts/pilot_closed_loop.py`
- Review target: `/Users/zhuge/Documents/codex/harness/scripts/adversarial_support_drill.py`
- Review target: `/Users/zhuge/Documents/codex/harness/scripts/high_intensity_support_drill.py`
- Review target: `/Users/zhuge/Documents/codex/harness/tests/test_knowledge_build.py`
- Review target: `/Users/zhuge/Documents/codex/harness/tests/test_cli.py`
- Review target: `/Users/zhuge/Documents/codex/harness/tests/test_pilot_readiness.py`
- Review target: `/Users/zhuge/Documents/codex/harness/tests/test_pilot_closed_loop.py`
- Review target: `/Users/zhuge/Documents/codex/harness/docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`
- Review target: `/Users/zhuge/Documents/codex/harness/docs/superpowers/plans/2026-04-09-sengent-knowledge-build-phase2.md`
- Review target: `/Users/zhuge/Documents/codex/harness/docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase3.md`
- Review target: `/Users/zhuge/Documents/codex/harness/docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase4.md`
- Review target: `/Users/zhuge/Documents/codex/harness/docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase5.md`
- Review target: `/Users/zhuge/Documents/codex/harness/docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase6.md`
- Review target: `/Users/zhuge/Documents/codex/harness/docs/superpowers/plans/2026-04-10-sengent-knowledge-build-phase7.md`

- [ ] **Step 1: Summarize current change scope and review target**

Use `git status`, `git diff --stat`, and targeted file reads to isolate the full renew-chain work that needs review.

- [ ] **Step 2: Dispatch a separate review thread**

Ask the review thread to inspect the full renew chain across:
- ingest/build/runtime boundaries
- review/apply/rollback operator flow
- eval gate integration
- contract drift between implementation, tests, and docs

Then inspect:
- architecture robustness
- functional completeness
- code quality / maintainability

Require concrete findings with file references and prioritized severity.

- [ ] **Step 3: Convert accepted findings into a remediation checklist**

Only fix issues that are technically justified and aligned with the project’s `rule-first + structured packs + eval-gated` constraints.

## Chunk 2: Remediation

### Task 2: Tighten implementation from review findings

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/knowledge_build.py`
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/cli.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_knowledge_build.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_cli.py`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`

- [ ] **Step 4: Add or adjust failing tests for each accepted finding**

Every behavior change must be locked by a failing test before production edits.

- [ ] **Step 5: Implement minimal fixes**

Keep fixes local to:
- activation/rollback safety
- operator workflow clarity
- manifest/report correctness
- maintainability cleanup directly justified by findings

- [ ] **Step 6: Re-run focused suites after each batch**

Run only the relevant tests first, then continue once green.

## Chunk 3: Verification, Commit, Handoff

### Task 3: Verify, commit, and document

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`
- Create: `/Users/zhuge/Documents/codex/harness/docs/superpowers/architecture/2026-04-10-sengent-knowledge-build-architecture.md`
- Create: `/Users/zhuge/Documents/codex/harness/docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`

- [ ] **Step 7: Run focused verification**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_cli.py`
Expected: PASS

Run: `python3.11 -m pytest -q tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py`
Expected: PASS

- [ ] **Step 8: Run full verification**

Run: `python3.11 -m pytest -q`
Expected: PASS

Run: `python3.11 scripts/pilot_readiness_eval.py`
Expected: all gates passed

Run: `python3.11 scripts/pilot_closed_loop.py`
Expected: quality score 100, risk level stable

- [ ] **Step 9: Commit reviewed work**

Stage only the intended files and create one intentional commit for:
- review tightening
- rollback safety
- operator handoff docs

- [ ] **Step 10: Write architecture diagram and maintainer manual**

Deliver:
- a system architecture doc with a diagram and explanation of data flow
- an operator manual covering add/update/delete/build/review/activate/rollback
