# Sengent 2.1 Hosted-LLM Architecture Plan

> **For agentic workers:** This tranche is `spec-first`. Do not implement `2.1` code until the revised architecture spec is considered stable. Use this document to sequence documentation and planning work, not to start runtime refactors.

**Goal:** Turn the `2.1` hosted-LLM direction into a formal architecture contract that preserves 2.0 governance and explicitly adds the missing layers surfaced by adversarial review.

**Architecture Direction:** `LLM-native, but governance-first`. Keep the `2.0` kernel/compiler/factory control surfaces, add explicit `Trust Boundary`, `Tool Arbitration`, `Boundary Pack`, `Capability-Based Adapter`, `Eval / Trace Plane`, and `Artifact Lifecycle` contracts, then only after that write the engineering implementation plan.

**Tech Stack Context:** Python 3.11 codebase, current `2.0` support kernel + knowledge compiler + factory draft assets, existing local/hosted model seams, current CLI/operator surfaces

---

## Priority Red Lines

- `Anti-Drift`, `Trust Boundary`, and `Tool Arbitration` must be fixed in the spec before any `2.1` implementation work begins.
- `2.1` means a lighter hosted runtime, not a lighter governance core.

## Current Stage Decision

`2.1` is authorized for:

- research
- formal architecture spec
- anti-drift contract writing
- engineering planning

`2.1` is not yet authorized for:

- runtime implementation
- hosted-runtime PoC code
- factory remote-provider integration
- migration of current runtime callers

## Scope Boundary For This Tranche

This tranche explicitly includes:

- revised `2.1` hosted-LLM architecture spec
- `Sengent Anti-Drift Principles`
- trust boundary definition
- tool arbitration definition
- capability-based adapter definition
- boundary pack definition
- eval / trace plane definition
- artifact lifecycle definition
- implementation-phase sequencing

This tranche explicitly excludes:

- code changes in `src/`
- test changes for `2.1`
- hosted adapter PoC
- doctor/runtime/CLI refactors
- raw retrieval expansion

## Durable 2.0 Control Surfaces To Keep

- active knowledge remains runtime truth
- build / review / gate / activate / rollback remain mandatory
- clarify-first remains stronger than retrieval breadth
- deterministic diagnostics remain first-class
- vendor/domain/playbook/incident layering remains explicit
- model output remains draft until promoted

## Deliverables

### Required Documentation

- `docs/superpowers/specs/2026-04-13-sengent-2-1-hosted-llm-architecture-design.md`
- `docs/superpowers/architecture/2026-04-13-sengent-2-1-anti-drift-principles.md`
- `docs/superpowers/plans/2026-04-13-sengent-2-1-hosted-llm-architecture.md`

### Required Architecture Content

The revised spec package must explicitly cover:

- hosted-LLM runtime assumption
- anti-drift invariants
- trust boundary layer
- tool arbitration layer
- capability-based LLM adapter
- boundary pack
- eval / trace plane
- artifact lifecycle
- internal hosted deployment recommendation
- `2.0 -> 2.1` stage discipline

## Phase 0: Establish The 2.1 Documentation Baseline

- [x] Push `codex/sengent-2.0` to GitHub
- [x] Create isolated `codex/sengent-2.1` worktree
- [x] Base `codex/sengent-2.1` on the `2.0` baseline

## Phase 1: Write The Revised 2.1 Spec Package

### Task 1: Revise the hosted-LLM architecture spec

**Files:**
- `docs/superpowers/specs/2026-04-13-sengent-2-1-hosted-llm-architecture-design.md`

- [x] **Step 1: Restate the product definition**

Must include:

- `Sengent = a bounded software support agent factory`
- `LLM-native, but governance-first`
- `2.1` is not full RAG

- [x] **Step 2: Restate the current-stage decision**

Must include:

- spec is authorized
- implementation is not yet authorized

- [x] **Step 3: Add adversarial-review upgrades**

Must include:

- trust boundary layer
- tool arbitration layer
- anti-drift invariants
- capability-based adapter
- boundary pack
- eval / trace plane
- artifact lifecycle

- [x] **Step 4: Revise the layer model**

Must include:

- Thin Client / CLI
- Support Control Layer
- Boundary Pack + Active Knowledge
- Tool Arbitration Layer
- Deterministic Diagnostics
- Capability-Based LLM Adapter
- Knowledge Factory
- Eval / Trace Plane
- Trust Boundary Layer

### Task 2: Revise the anti-drift document

**Files:**
- `docs/superpowers/architecture/2026-04-13-sengent-2-1-anti-drift-principles.md`

- [x] **Step 1: Promote principles to invariants**

Must include:

- runtime never reads raw ingestion directly as truth
- model output is draft only unless promoted
- tool-required intents cannot be answered from model-only reasoning
- knowledge layers remain explicit
- rollback always stays available

- [x] **Step 2: Add trust-boundary review discipline**

Must include:

- outbound-context control
- redaction expectation
- local-only context rule

### Task 3: Revise the plan itself so it stays pre-implementation**

**Files:**
- `docs/superpowers/plans/2026-04-13-sengent-2-1-hosted-llm-architecture.md`

- [x] **Step 1: Remove direct implementation sequencing from the current tranche**
- [x] **Step 2: Reframe the plan as `spec -> implementation plan -> internal PoC`**

## Phase 2: Write The Engineering Implementation Plan

This phase begins only after the revised spec package is considered stable.

Recommended implementation-plan breakdown:

1. `anti-drift + trust boundary contracts`
2. `capability-based LLM adapter`
3. `tool arbitration + boundary pack`
4. `eval / trace plane`
5. `internal hosted runtime PoC`
6. `2.0 -> 2.1 migration path`

### Exit Criteria For Phase 2

Before phase 2 is considered complete, the engineering plan must clearly state:

- which code areas move first
- which control surfaces stay frozen
- which tests/evals prove anti-drift
- what the PoC is allowed to do
- what the PoC is forbidden to do

## Phase 3: Internal PoC

This phase begins only after the engineering implementation plan is complete.

The first PoC should stay minimal:

- one hosted adapter
- one internal config surface
- preserve current knowledge compiler / active knowledge
- keep deterministic diagnostics
- no customer packaging yet

### PoC Non-Goals

- do not rewrite the support kernel
- do not bypass build / review / gate / activate
- do not make runtime read raw docs as truth
- do not ship shared credentials in packaging

## Recommended Main-Thread Behavior

Until phase 2 starts, the main thread should do only these things:

- maintain the revised spec package
- keep the `2.1` worktree isolated
- reject premature implementation drift
- use subthreads only for documentation/planning support when needed

The main thread should not:

- dispatch `2.1` runtime refactors
- land hosted adapter code
- move doctor/runtime/CLI toward hosted implementation yet

## Verification For This Tranche

This tranche should only require documentation verification.

Run:

```bash
python3.11 -m pytest -q tests/test_docs_contract.py
```

Expected: PASS

## Success Criteria

This tranche succeeds when:

- the revised `2.1` spec exists as a formal contract
- anti-drift is documented as system invariants
- trust boundary / tool arbitration / boundary pack / eval plane / artifact lifecycle are explicit
- the execution order is constrained to `spec -> plan -> PoC`
- the branch remains free of premature `2.1` implementation work
