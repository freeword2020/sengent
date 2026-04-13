# Sengent 2.0 Support Optimization Roadmap

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After Phase 5 closes the maintainer review loop, evolve `Sengent 2.0` from a technically correct support kernel into a lower-maintenance, higher-trust, more user-visible support system for `Sentieon`.

**Architecture:** Keep the current `Support Kernel -> Knowledge Compiler -> Active Knowledge` path stable. This roadmap adds the next two outer layers in sequence: first the `Knowledge Factory` entrypoints that reduce maintainer toil, then the `support experience` improvements that make runtime answers feel more useful and directed for end users.

**Tech Stack:** Python 3.11, pytest, existing knowledge build / review / gate pipeline, local JSONL/YAML artifacts, current CLI and chat runtime, future optional large-model factory interface

---

## Dependency Boundary

This roadmap assumes:

- the existing 2.0 foundation is in place
- Milestone 4 controlled learning loop is complete
- **Milestone 5 (`gap triage + eval seeding`) must land first**

Do not start the support-optimization implementation tasks below until the Phase 5 work in:

- `docs/superpowers/plans/2026-04-13-sengent-2-0-milestone-5-gap-triage-and-eval-seeding.md`

is complete and verified.

## Scope Boundary

This roadmap covers the work that should happen **after** Phase 5:

- minimal Knowledge Factory contracts
- source intake convenience for official/domain materials
- review-queue and maintainer convenience improvements
- front-end support answer UX improvements
- dataset export and future large-model factory interface preparation

This roadmap does **not** include:

- multi-vendor implementation
- online training
- runtime auto-activation
- replacing the current kernel with a new agent architecture

## File Map

The roadmap is expected to create work in these clusters:

- `docs/superpowers/specs/...`
  - sub-specs for intake, UX, and dataset export
- `docs/superpowers/plans/...`
  - phase-specific implementation plans
- `src/sentieon_assist/`
  - factory-side modules for intake, candidate generation, review utilities
  - runtime-side UX rendering and answer-shaping improvements
- `tests/`
  - coverage for intake, review, UX, and dataset export

## Chunk 0: Phase 5 Completion Gate

### Task 0: Treat Phase 5 as the hard prerequisite

**Files:**
- Reference only: `docs/superpowers/plans/2026-04-13-sengent-2-0-milestone-5-gap-triage-and-eval-seeding.md`

- [ ] **Step 1: Verify Phase 5 is complete**

Require fresh verification that:

- `knowledge triage-gap` exists
- `gap_intake_review.jsonl` is decision-aware
- `gap_eval_seed.jsonl` exists and is populated through rebuild
- operator docs describe the maintainer review loop

- [ ] **Step 2: Confirm the post-Phase-5 baseline**

Only proceed once the codebase demonstrates:

- runtime gap -> inbox artifact
- inbox artifact -> triage metadata
- triaged gap -> eval seed
- eval seed -> gate input

Expected result: the first `Sentieon` support-learning loop is fully closed offline.

## Chunk 1: Knowledge Factory Minimum Viable Entry Points

### Task 1: Add the first factory-side source intake flow

**Goal:** Reduce maintainer toil by making official/domain material ingestion a first-class workflow instead of a manual file-drop habit.

**Files:**
- Create: `docs/superpowers/specs/<date>-sengent-2-0-source-intake-design.md`
- Create: `docs/superpowers/plans/<date>-sengent-2-0-source-intake.md`
- Expected code area later: `src/sentieon_assist/source_intake.py`
- Expected tests later: `tests/test_source_intake.py`

- [ ] **Step 1: Define intake source classes**

The design must distinguish:

- vendor official docs
- release notes
- domain standards
- support cases / incidents
- maintainer-authored notes

- [ ] **Step 2: Define the standard output contract**

Every intake source should produce:

- inbox-ready markdown or parsed artifact
- sidecar metadata
- source provenance
- review hints

- [ ] **Step 3: Keep the boundary explicit**

Factory intake may prepare or normalize content, but it must still output into inbox/build rather than active runtime.

## Chunk 2: Maintainer Convenience Refactor

### Task 2: Make review/build output more actionable and less manual

**Goal:** Shift maintainer work from authoring raw knowledge to reviewing candidate knowledge.

**Files:**
- Create: `docs/superpowers/specs/<date>-sengent-2-0-maintainer-experience-design.md`
- Create: `docs/superpowers/plans/<date>-sengent-2-0-maintainer-experience.md`
- Expected code areas later:
  - `src/sentieon_assist/knowledge_review.py`
  - `src/sentieon_assist/cli.py`
- Expected tests later:
  - `tests/test_knowledge_review.py`
  - `tests/test_cli.py`

- [ ] **Step 1: Define the maintainer queue model**

At minimum the system should surface:

- pending gap triage
- pending source-review candidates
- contradiction findings
- candidate pack diffs
- eval seeds awaiting gate consumption

- [ ] **Step 2: Define the operator-friendly next actions**

For each review bucket, the system should be able to tell the maintainer:

- what this item is
- why it matters
- what to do next
- what command or UI action resolves it

- [ ] **Step 3: Preserve CLI completeness**

Even if a future light UI is added, the full maintainer workflow must remain available via CLI.

## Chunk 3: User Support Experience Upgrade

### Task 3: Improve answer presentation and guided clarification

**Goal:** Make the user-facing support experience feel more directed, less stiff, and more obviously useful without relaxing runtime evidence discipline.

**Files:**
- Create: `docs/superpowers/specs/<date>-sengent-2-0-support-experience-design.md`
- Create: `docs/superpowers/plans/<date>-sengent-2-0-support-experience.md`
- Expected code areas later:
  - `src/sentieon_assist/chat_ui.py`
  - `src/sentieon_assist/answer_contracts.py`
  - `src/sentieon_assist/cli.py`
- Expected tests later:
  - `tests/test_chat_ui.py`
  - `tests/test_cli.py`
  - `tests/test_answering.py`

- [ ] **Step 1: Formalize the answer card contract**

Support answers should visibly separate:

- current judgment
- evidence
- scope or boundaries
- recommended next step
- needed clarification if blocked

- [ ] **Step 2: Design the gap upload / clarification affordance**

When runtime lacks evidence, the user experience should show:

- what is missing
- why it matters
- how to provide it

This must map cleanly back into the offline knowledge loop.

- [ ] **Step 3: Improve perceived competence without fake behavior**

Do not simulate tool use or fabricate certainty. UX gains must come from better answer structure and better directed interaction.

## Chunk 4: Dataset Export And Future Model Adapter Preparation

### Task 4: Prepare training assets without turning models into the knowledge base

**Goal:** Make it possible to train stronger support behavior later without changing the source of truth for facts.

**Files:**
- Create: `docs/superpowers/specs/<date>-sengent-2-0-dataset-export-design.md`
- Create: `docs/superpowers/plans/<date>-sengent-2-0-dataset-export.md`
- Expected code area later: `src/sentieon_assist/dataset_export.py`
- Expected tests later: `tests/test_dataset_export.py`

- [ ] **Step 1: Define supported training asset classes**

At minimum:

- gold support answers
- clarified gap cases
- incident/playbook exemplars
- reject / boundary exemplars

- [ ] **Step 2: Define export provenance**

Every exported sample should retain:

- vendor id
- source artifact
- review provenance
- expected answer contract fields

- [ ] **Step 3: Keep training downstream**

Training artifacts should be exportable, but no training workflow should be embedded into runtime or compiler critical paths.

## Chunk 5: Large-Model Factory Interface

### Task 5: Add a future-safe extension point for larger models

**Goal:** Prepare for a bigger-model assistant in the factory layer without making runtime depend on it.

**Files:**
- Create: `docs/superpowers/specs/<date>-sengent-2-0-factory-model-interface-design.md`
- Create: `docs/superpowers/plans/<date>-sengent-2-0-factory-model-interface.md`

- [ ] **Step 1: Restrict the interface to offline factory tasks**

Allowable uses:

- candidate extraction
- incident normalization
- contradiction clustering
- dataset drafting

Disallowed uses:

- direct runtime answering
- automatic fact override
- direct active-pack mutation

- [ ] **Step 2: Define auditability requirements**

Every model-produced artifact should retain:

- prompt or template provenance
- source references
- review-needed status

## Recommended Execution Order

After Phase 5 lands, execute the next work in this order:

1. Knowledge Factory source intake
2. Maintainer convenience refactor
3. User support experience upgrade
4. Dataset export
5. Large-model factory interface

This order is deliberate:

- first reduce knowledge-maintenance cost
- then improve maintainer flow
- then improve user-visible value
- only after that add training/export/model-adapter complexity

## Sentieon-First Delivery Strategy

For all chunks above:

- build only what `Sentieon` needs first
- keep contracts vendor-agnostic
- do not generalize for a second vendor until the `Sentieon` flow is proven

## Success Criteria

This roadmap is complete when:

1. `Sentieon` knowledge maintenance is materially easier than manual curation.
2. Maintainers mainly review candidates rather than authoring raw structured entries.
3. Users can see clearer judgment, evidence, and next-step guidance in support responses.
4. Training assets can be exported from audited support traces without replacing the formal knowledge base.
5. A future larger model can be added to the factory layer without changing runtime truth rules.
