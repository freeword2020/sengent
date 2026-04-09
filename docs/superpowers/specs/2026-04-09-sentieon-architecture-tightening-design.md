# Sentieon Architecture Tightening Design

## Context

`Sengent` now has a workable rule-first support architecture:

- `cli.py` owns shell I/O
- `support_coordinator.py` owns top-level support routing and chat follow-up reuse
- `answering.py` composes troubleshooting and reference answers
- `reference_intents.py`, `workflow_index.py`, `module_index.py`, and
  `external_guides.py` provide deterministic reference-domain behavior
- `sentieon-note/` holds the current structured local evidence base

The system is already usable for many common support prompts, but the
responsibility boundaries are still too loose. Several layers currently make
decisions that belong to neighboring layers, which makes the code harder to
reason about and easier to regress.

## Problem Statement

The current system does not mainly suffer from missing layers. It suffers from
layer drift.

### Drift 1: Top-Level Coordinator Knows Too Much About Reference Subtypes

`support_coordinator.py` currently contains:

- capability-question detection
- top-level route priority
- follow-up reuse planning
- clarification-slot inference support
- reference-domain subtype heuristics such as:
  - license doc prompts (`LICCLNT` / `LICSRVR`)
  - operational documentation prompts (`CPU`, `GPU`, `sentieon driver` vs
    `sentieon-cli`)
  - selected boundary prompts (`BWA-turbo`, `SVSolver`)

This means the coordinator is no longer just answering:

- is this troubleshooting, onboarding, reference, or capability?

It is also answering:

- which kind of reference question is this?

That is the wrong level of abstraction.

### Drift 2: Reference-Domain Intent Ownership Is Split

`reference_intents.py` already owns a meaningful amount of reference-domain
understanding:

- module intro
- parameter lookup
- script example
- workflow guidance
- external-reference fallback

But a second chunk of reference recognition lives in
`support_coordinator.py`. The result is that the same prompt can become
reference lookup for two different reasons depending on which heuristic fires
first.

### Drift 3: Answering Still Carries Some Routing Semantics

`answering.py` should answer the selected task. It currently also decides
between several reference-domain pre-answer paths:

- doc-style explanations
- reference boundaries
- workflow-guidance handoff to direct script answers
- external error association vs external guide vs module answer preference

These are all still reference-domain concerns. They are legitimate, but they
should be treated as a dedicated reference-resolution stage rather than an
informal pile inside a general answer composer.

### Drift 4: Knowledge Files Mix Facts With Execution Hints

`workflow-guides.json` and `sentieon-modules.json` now carry both:

- factual knowledge
- routing metadata such as `script_module` and `direct_script_handoff`

This is acceptable for the current stage, but only if the runtime contract is
explicit. Right now that contract exists in code behavior more than in named
schema responsibilities.

## Design Goal

Tighten responsibilities without replacing the current rule-first architecture.

This is a contraction pass, not a redesign. The goal is to make each layer do
less, not add more machinery.

## Target Responsibility Model

### 1. `cli.py`

Owns only:

- command parsing
- chat shell I/O
- model warmup and streaming hooks
- session-loop orchestration

Must not own:

- support route priority
- reference subtype classification
- raw semantic context concatenation policy

### 2. `support_coordinator.py`

Owns only:

- top-level task selection
  - `troubleshooting`
  - `onboarding_guidance`
  - `reference_lookup`
  - `capability_explanation`
- task switching
- follow-up reuse planning
- support-state transitions

Must not own:

- reference-domain subtype heuristics
- reference boundary tagging
- document-style reference topic detection
- knowledge-source preference

### 3. `reference_intents.py`

Owns:

- reference-domain intent parsing
- high-signal reference heuristics
- explicit module hints
- operational doc-style reference recognition
- boundary-prone reference recognition when the result still belongs to
  `reference_lookup`

Must not own:

- chat state
- support-task switching
- answer formatting

### 4. `answering.py`

Owns:

- troubleshooting answer composition
- capability explanation answer composition
- invocation of the reference-domain answer path

Must not own:

- top-level task selection
- ad hoc reclassification from one support task to another

### 5. Reference-Domain Resolution

The reference answer path should be treated as a dedicated internal stage with
this order:

1. doc-style deterministic answer
2. boundary answer
3. workflow-guidance answer or script handoff
4. external association / external guide
5. module / parameter / script answer
6. model fallback only after local evidence assembly

For the current stage, this may stay inside `answering.py`, but the contract
must be explicit and testable.

### 6. Knowledge Files

`workflow-guides.json` and `sentieon-modules.json` may continue to carry both
facts and runtime hints, but the hints must be named as such.

The runtime should treat:

- `summary`, `guidance`, `inputs`, `outputs`, `parameters` as factual content
- `script_module`, `direct_script_handoff`, `priority`, `prefer_any`,
  `exclude_any` as retrieval / routing hints

## P0 Tightening Scope

This pass focuses on the highest-leverage contraction:

### P0-A

Move operational reference subtype recognition out of
`support_coordinator.py` and into `reference_intents.py`.

Prompts in scope:

- CPU / threads / `-t`
- GPU / FPGA / ARM / Graviton compatibility
- `sentieon driver` vs `sentieon-cli`
- `LICCLNT` / `LICSRVR` tool-selection prompts
- boundary-prone `BWA-turbo` / `SVSolver` style prompts

### P0-B

Simplify `support_coordinator.select_support_route()` so it decides only:

- troubleshooting
- capability explanation
- onboarding guidance
- reference lookup

It should no longer contain special-case reference subtype branches for the
prompts above.

### P0-C

Add regression tests that prove the tightened contract:

- `parse_reference_intent()` recognizes doc-style reference prompts as
  `reference_other`
- `parse_reference_intent()` recognizes selected boundary-prone prompts as
  `reference_other`
- `select_support_route()` routes these prompts to `reference_lookup` through
  parsed reference intent instead of coordinator-local subtype branches

## P1 Tightening Scope

- Extract the reference-domain pre-answer stage behind an explicit helper or
  resolver boundary
- reduce ad hoc routing knowledge inside `answering.py`
- document the knowledge-file field contract in `sentieon-note/README.md`

## P2 Tightening Scope

- split retrieval hints from factual content if the current JSON format becomes
  too hard to maintain
- introduce a dedicated retrieval broker only after the existing contracts are
  stable

## Non-Goals

- replacing the current rule-first architecture with full RAG
- making the LLM the primary route owner
- broad refactoring of UI or CLI presentation
- changing customer-facing answer style unless required by boundary tightening

## Success Criteria

The tightening pass succeeds if:

1. coordinator code becomes simpler without losing current answer coverage
2. reference-domain subtype ownership becomes more centralized
3. current user-facing behavior for supported prompts remains stable
4. adversarial drill coverage remains green
5. future additions of new reference prompts mostly require changes in
   `reference_intents.py` or reference-domain sources, not in the coordinator
