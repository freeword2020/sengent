# Sengent 2.1 Engineering Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the revised `Sengent 2.1` architecture into a staged implementation sequence that lands hard governance contracts before any hosted-runtime PoC code.

**Architecture:** `2.1` stays `LLM-native, but governance-first`. The runtime may become lighter and hosted-first, but the governance core stays intact: active knowledge remains truth, deterministic diagnostics remain first-class, and every runtime/provider upgrade is gated by explicit anti-drift, trust-boundary, and tool-arbitration contracts.

**Tech Stack:** Python 3.11, pytest, current `sentieon_assist` CLI/runtime/compiler/factory modules, local JSON/JSONL artifacts, existing support contracts, session-event traces, and factory draft artifacts

---

## Priority Red Lines

- `Anti-Drift`, `Trust Boundary`, and `Tool Arbitration` must land as code-level contracts before the hosted runtime PoC.
- `2.1` means a lighter hosted runtime, not a lighter governance core.
- No chunk may make runtime read raw ingestion directly as truth.
- No chunk may let model output bypass `build / review / gate / activate`.

## Execution Rule

This document is the last planning artifact before code phase.

Execution order is fixed:

1. `anti-drift + trust boundary`
2. `capability-based adapter`
3. `tool arbitration + boundary pack`
4. `eval / trace plane`
5. `internal hosted runtime PoC`

Do not skip ahead.

## Frozen Control Surfaces

The following remain frozen across all chunks unless a chunk explicitly says otherwise:

- active knowledge as runtime truth source
- build / review / gate / activate / rollback
- vendor/domain/playbook/incident layering
- clarify-first
- deterministic diagnostics as first-class control plane
- factory output as `draft` until promoted

## File Map

### Chunk 1: Anti-Drift + Trust Boundary

- Create: `src/sentieon_assist/runtime_invariants.py`
  - central invariants and promotion-state enums
- Create: `src/sentieon_assist/trust_boundary.py`
  - outbound-context policy, redaction rules, local-only markers
- Modify: `src/sentieon_assist/session_events.py`
  - trace outbound-context summaries and redaction/provenance metadata
- Modify: `src/sentieon_assist/factory_model.py`
  - artifact lifecycle states and trust-boundary provenance on draft artifacts
- Create: `tests/test_runtime_invariants.py`
- Create: `tests/test_trust_boundary.py`
- Modify: `tests/test_session_events.py`
- Modify: `tests/test_factory_model.py`

### Chunk 2: Capability-Based Adapter

- Create: `src/sentieon_assist/llm_capabilities.py`
  - provider capability descriptors
- Modify: `src/sentieon_assist/config.py`
  - canonical runtime provider config and capability-aware settings
- Modify: `src/sentieon_assist/llm_backends.py`
  - provider capability plumbing
- Modify: `src/sentieon_assist/doctor.py`
  - provider-aware diagnostics input
- Modify: `src/sentieon_assist/runtime_guidance.py`
  - provider-aware runtime guidance
- Modify: `src/sentieon_assist/cli.py`
  - provider-aware doctor/runtime wiring
- Modify: `tests/test_config.py`
- Modify: `tests/test_llm_backends.py`
- Modify: `tests/test_doctor.py`
- Modify: `tests/test_runtime_guidance.py`
- Modify: `tests/test_cli.py`

### Chunk 3: Tool Arbitration + Boundary Pack

- Create: `src/sentieon_assist/tool_arbitration.py`
  - must-tool / must-clarify / must-refuse / must-escalate decisions
- Create: `src/sentieon_assist/boundary_pack.py`
  - boundary-pack contract and loader/runtime helpers
- Modify: `src/sentieon_assist/support_contracts.py`
  - explicit tool-required and refusal/escalation fields
- Modify: `src/sentieon_assist/support_coordinator.py`
  - route decisions through tool arbitration and boundary pack
- Modify: `src/sentieon_assist/answering.py`
  - answer rendering honors arbitration outcomes
- Modify: `src/sentieon_assist/reference_resolution.py`
  - reference answers honor must-tool / boundary constraints
- Modify: `src/sentieon_assist/reference_intents.py`
  - intent layer can mark tool-required cases
- Modify: `src/sentieon_assist/trace_vocab.py`
  - new resolver/arbitration trace labels
- Create: `tests/test_tool_arbitration.py`
- Create: `tests/test_boundary_pack.py`
- Modify: `tests/test_support_coordinator.py`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_reference_intents.py`
- Modify: `tests/test_reference_resolution.py`

### Chunk 4: Eval / Trace Plane

- Create: `src/sentieon_assist/eval_trace_plane.py`
  - normalized runtime/factory trace projection for eval and review
- Modify: `src/sentieon_assist/session_events.py`
  - persist eval-facing fields
- Modify: `src/sentieon_assist/dataset_export.py`
  - export boundary/tool/clarify/evidence fidelity fields
- Modify: `src/sentieon_assist/gap_review.py`
  - review/eval alignment for captured gaps
- Modify: `src/sentieon_assist/knowledge_review.py`
  - review queue surfaces artifact lifecycle and eval/trust metadata
- Modify: `src/sentieon_assist/factory_model.py`
  - lifecycle compatibility with eval/trace plane
- Create: `tests/test_eval_trace_plane.py`
- Modify: `tests/test_session_events.py`
- Modify: `tests/test_dataset_export.py`
- Modify: `tests/test_gap_review.py`
- Modify: `tests/test_knowledge_review.py`
- Modify: `tests/test_factory_model.py`

### Chunk 5: Internal Hosted Runtime PoC

- Modify: `src/sentieon_assist/config.py`
- Modify: `src/sentieon_assist/llm_backends.py`
- Modify: `src/sentieon_assist/doctor.py`
- Modify: `src/sentieon_assist/runtime_guidance.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/reference_intents.py`
- Modify: `src/sentieon_assist/support_coordinator.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_llm_backends.py`
- Modify: `tests/test_doctor.py`
- Modify: `tests/test_runtime_guidance.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_reference_intents.py`
- Modify: `tests/test_support_coordinator.py`

## Chunk 1: Anti-Drift + Trust Boundary Contracts

### Task 1: Add failing invariant and trust-boundary tests

**Files:**
- Create: `tests/test_runtime_invariants.py`
- Create: `tests/test_trust_boundary.py`
- Modify: `tests/test_session_events.py`
- Modify: `tests/test_factory_model.py`

- [ ] **Step 1: Write invariant tests**

Cover:

- raw ingestion cannot be classified as runtime truth
- model outputs default to draft/pending promotion
- tool-required intents are explicitly representable
- unknown truth-source or promotion-state values fail clearly

- [ ] **Step 2: Write trust-boundary tests**

Cover:

- outbound context items can be marked `allowed`, `redacted`, or `local_only`
- local-only items never survive outbound filtering
- redacted fields keep provenance but remove raw values

- [ ] **Step 3: Extend session/factory tests**

Cover:

- session events can persist trust-boundary summaries
- factory draft artifacts include lifecycle state and trust-boundary provenance

- [ ] **Step 4: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_runtime_invariants.py tests/test_trust_boundary.py tests/test_session_events.py tests/test_factory_model.py -k "invariant or trust_boundary or lifecycle"
```

Expected: FAIL because these contracts do not exist yet.

### Task 2: Implement the invariant/trust-boundary contract layer

**Files:**
- Create: `src/sentieon_assist/runtime_invariants.py`
- Create: `src/sentieon_assist/trust_boundary.py`
- Modify: `src/sentieon_assist/session_events.py`
- Modify: `src/sentieon_assist/factory_model.py`

- [ ] **Step 1: Implement `runtime_invariants.py`**

Include:

- truth-source enum/normalizer
- promotion-state enum/normalizer
- tool-requirement enum/normalizer
- helper predicates for anti-drift checks

- [ ] **Step 2: Implement `trust_boundary.py`**

Include:

- outbound context item dataclass
- trust-boundary decision/result dataclass
- redaction helpers
- local-only filtering helper

- [ ] **Step 3: Thread provenance into session/factory artifacts**

Requirements:

- session events expose outbound-context summary, not raw secret values
- factory drafts record lifecycle state and trust-boundary provenance
- no runtime truth behavior changes in this chunk

- [ ] **Step 4: Run focused tests and verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_runtime_invariants.py tests/test_trust_boundary.py tests/test_session_events.py tests/test_factory_model.py -k "invariant or trust_boundary or lifecycle"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/runtime_invariants.py src/sentieon_assist/trust_boundary.py src/sentieon_assist/session_events.py src/sentieon_assist/factory_model.py tests/test_runtime_invariants.py tests/test_trust_boundary.py tests/test_session_events.py tests/test_factory_model.py
git commit -m "feat: add 2.1 trust boundary contracts"
```

## Chunk 2: Capability-Based Adapter

### Task 3: Add failing capability-adapter tests

**Files:**
- Create: `src/sentieon_assist/llm_capabilities.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_llm_backends.py`
- Modify: `tests/test_doctor.py`
- Modify: `tests/test_runtime_guidance.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add config tests for capability-aware provider settings**

Cover:

- provider id, base URL, model, API key, optional headers/settings
- provider capabilities such as `supports_streaming` and `supports_json_schema`
- unsupported provider capability values fail clearly

- [ ] **Step 2: Add backend-router tests**

Cover:

- router can build providers with explicit capability descriptors
- `openai_compatible` does not assume all providers support identical features

- [ ] **Step 3: Add diagnostics tests**

Cover:

- doctor/runtime guidance can describe provider capability mismatches
- hosted providers do not emit Ollama-specific remediation

- [ ] **Step 4: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_config.py tests/test_llm_backends.py tests/test_doctor.py tests/test_runtime_guidance.py tests/test_cli.py -k "provider or capability or runtime"
```

Expected: FAIL because capability-based runtime config is not wired yet.

### Task 4: Implement the capability-based adapter layer

**Files:**
- Create: `src/sentieon_assist/llm_capabilities.py`
- Modify: `src/sentieon_assist/config.py`
- Modify: `src/sentieon_assist/llm_backends.py`
- Modify: `src/sentieon_assist/doctor.py`
- Modify: `src/sentieon_assist/runtime_guidance.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Implement `llm_capabilities.py`**

Include:

- provider capability dataclass
- normalizers for capability flags
- default descriptors for `ollama` and `openai_compatible`

- [ ] **Step 2: Rebuild runtime config around capabilities**

Requirements:

- config can describe provider + capabilities cleanly
- compatibility aliases from current Ollama-first env vars remain available
- no shared API key packaging assumptions

- [ ] **Step 3: Rebuild backend/doctor/runtime guidance surfaces**

Requirements:

- backend router uses provider capability descriptors
- doctor reports provider reachability and capability mismatch clearly
- runtime guidance uses provider-aware remediation

- [ ] **Step 4: Run focused tests and verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_config.py tests/test_llm_backends.py tests/test_doctor.py tests/test_runtime_guidance.py tests/test_cli.py -k "provider or capability or runtime"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/llm_capabilities.py src/sentieon_assist/config.py src/sentieon_assist/llm_backends.py src/sentieon_assist/doctor.py src/sentieon_assist/runtime_guidance.py src/sentieon_assist/cli.py tests/test_config.py tests/test_llm_backends.py tests/test_doctor.py tests/test_runtime_guidance.py tests/test_cli.py
git commit -m "feat: add capability based runtime adapter"
```

## Chunk 3: Tool Arbitration + Boundary Pack

### Task 5: Add failing arbitration and boundary-pack tests

**Files:**
- Create: `tests/test_tool_arbitration.py`
- Create: `tests/test_boundary_pack.py`
- Modify: `tests/test_support_coordinator.py`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_reference_intents.py`
- Modify: `tests/test_reference_resolution.py`

- [ ] **Step 1: Add boundary-pack tests**

Cover:

- pack can encode `should-answer`, `must-clarify`, `must-tool`, `must-refuse`, `must-escalate`
- version-sensitive boundary rules are representable
- invalid boundary entries fail clearly

- [ ] **Step 2: Add tool-arbitration tests**

Cover:

- file-format/structure cases route to `must-tool`
- model-only reasoning cannot satisfy `must-tool`
- clarify-first still wins when required fields are missing

- [ ] **Step 3: Add runtime integration tests**

Cover:

- support coordinator exposes arbitration outcome
- answering/reference resolution honor must-tool and refusal paths
- trace labels persist boundary/arbitration outcome

- [ ] **Step 4: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_tool_arbitration.py tests/test_boundary_pack.py tests/test_support_coordinator.py tests/test_answering.py tests/test_reference_intents.py tests/test_reference_resolution.py -k "must_tool or boundary_pack or arbitration or refuse or escalate"
```

Expected: FAIL because arbitration and boundary-pack runtime do not exist yet.

### Task 6: Implement tool arbitration and boundary-pack runtime

**Files:**
- Create: `src/sentieon_assist/tool_arbitration.py`
- Create: `src/sentieon_assist/boundary_pack.py`
- Modify: `src/sentieon_assist/support_contracts.py`
- Modify: `src/sentieon_assist/support_coordinator.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/reference_resolution.py`
- Modify: `src/sentieon_assist/reference_intents.py`
- Modify: `src/sentieon_assist/trace_vocab.py`

- [ ] **Step 1: Implement `boundary_pack.py`**

Include:

- boundary rule dataclass
- boundary pack loader/normalizer
- version-sensitive rule matching helper

- [ ] **Step 2: Implement `tool_arbitration.py`**

Include:

- tool-required intent classifier
- arbitration decision/result type
- helper for “model may explain tool output but not replace tool”

- [ ] **Step 3: Integrate arbitration into runtime caller path**

Requirements:

- support coordinator and answer/reference layers honor arbitration outcome
- must-tool and must-refuse do not fall back to free-form model answers
- clarify-first remains intact

- [ ] **Step 4: Run focused tests and verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_tool_arbitration.py tests/test_boundary_pack.py tests/test_support_coordinator.py tests/test_answering.py tests/test_reference_intents.py tests/test_reference_resolution.py -k "must_tool or boundary_pack or arbitration or refuse or escalate"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/tool_arbitration.py src/sentieon_assist/boundary_pack.py src/sentieon_assist/support_contracts.py src/sentieon_assist/support_coordinator.py src/sentieon_assist/answering.py src/sentieon_assist/reference_resolution.py src/sentieon_assist/reference_intents.py src/sentieon_assist/trace_vocab.py tests/test_tool_arbitration.py tests/test_boundary_pack.py tests/test_support_coordinator.py tests/test_answering.py tests/test_reference_intents.py tests/test_reference_resolution.py
git commit -m "feat: add 2.1 tool arbitration and boundary pack"
```

## Chunk 4: Eval / Trace Plane

### Task 7: Add failing eval/trace tests

**Files:**
- Create: `tests/test_eval_trace_plane.py`
- Modify: `tests/test_session_events.py`
- Modify: `tests/test_dataset_export.py`
- Modify: `tests/test_gap_review.py`
- Modify: `tests/test_knowledge_review.py`
- Modify: `tests/test_factory_model.py`

- [ ] **Step 1: Add eval-trace projection tests**

Cover:

- runtime traces can project factual/boundary/tool/clarify/refusal dimensions
- trust-boundary metadata survives into the eval plane
- artifact lifecycle survives into review/eval surfaces

- [ ] **Step 2: Add export/review tests**

Cover:

- dataset export includes evidence-fidelity and boundary-adherence fields
- knowledge review surfaces lifecycle state and eval/trust metadata

- [ ] **Step 3: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_eval_trace_plane.py tests/test_session_events.py tests/test_dataset_export.py tests/test_gap_review.py tests/test_knowledge_review.py tests/test_factory_model.py -k "eval or trace or lifecycle or evidence_fidelity"
```

Expected: FAIL because the dedicated eval/trace plane does not exist yet.

### Task 8: Implement the eval/trace plane

**Files:**
- Create: `src/sentieon_assist/eval_trace_plane.py`
- Modify: `src/sentieon_assist/session_events.py`
- Modify: `src/sentieon_assist/dataset_export.py`
- Modify: `src/sentieon_assist/gap_review.py`
- Modify: `src/sentieon_assist/knowledge_review.py`
- Modify: `src/sentieon_assist/factory_model.py`

- [ ] **Step 1: Implement `eval_trace_plane.py`**

Include:

- normalized runtime/factory trace projection
- boundary/tool/clarify/refusal/evidence-fidelity fields
- lifecycle-aware review projection

- [ ] **Step 2: Thread eval fields through existing artifacts**

Requirements:

- session events remain backward-compatible where possible
- dataset export stays review-grounded
- factory artifacts keep lifecycle state explicit

- [ ] **Step 3: Run focused tests and verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_eval_trace_plane.py tests/test_session_events.py tests/test_dataset_export.py tests/test_gap_review.py tests/test_knowledge_review.py tests/test_factory_model.py -k "eval or trace or lifecycle or evidence_fidelity"
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/sentieon_assist/eval_trace_plane.py src/sentieon_assist/session_events.py src/sentieon_assist/dataset_export.py src/sentieon_assist/gap_review.py src/sentieon_assist/knowledge_review.py src/sentieon_assist/factory_model.py tests/test_eval_trace_plane.py tests/test_session_events.py tests/test_dataset_export.py tests/test_gap_review.py tests/test_knowledge_review.py tests/test_factory_model.py
git commit -m "feat: add 2.1 eval trace plane"
```

## Chunk 5: Internal Hosted Runtime PoC

### Task 9: Add failing PoC/runtime regression tests

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_llm_backends.py`
- Modify: `tests/test_doctor.py`
- Modify: `tests/test_runtime_guidance.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_reference_intents.py`
- Modify: `tests/test_support_coordinator.py`

- [ ] **Step 1: Add hosted-runtime PoC tests**

Cover:

- one hosted provider can be primary runtime adapter
- deterministic diagnostics still run
- tool-required cases still do not bypass tool arbitration
- active knowledge remains truth source

- [ ] **Step 2: Add broader regression expectations**

Cover:

- reference and troubleshooting routes still obey clarify-first
- capability explanation remains stable
- no raw-ingestion truth path appears in CLI/runtime behavior

- [ ] **Step 3: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_config.py tests/test_llm_backends.py tests/test_doctor.py tests/test_runtime_guidance.py tests/test_cli.py tests/test_answering.py tests/test_reference_intents.py tests/test_support_coordinator.py -k "hosted or provider or tool or boundary or clarify"
```

Expected: FAIL until the PoC wiring is complete.

### Task 10: Implement the minimal internal hosted runtime PoC

**Files:**
- Modify: `src/sentieon_assist/config.py`
- Modify: `src/sentieon_assist/llm_backends.py`
- Modify: `src/sentieon_assist/doctor.py`
- Modify: `src/sentieon_assist/runtime_guidance.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/reference_intents.py`
- Modify: `src/sentieon_assist/support_coordinator.py`

- [ ] **Step 1: Wire a single internal hosted provider through the capability-based adapter**

Requirements:

- one hosted adapter
- one internal config surface
- no gateway dependency yet

- [ ] **Step 2: Keep runtime bounded by existing governance**

Requirements:

- active knowledge remains truth
- deterministic diagnostics remain in front of model-only reasoning where required
- build/compiler/factory governance does not regress

- [ ] **Step 3: Run focused tests and verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_config.py tests/test_llm_backends.py tests/test_doctor.py tests/test_runtime_guidance.py tests/test_cli.py tests/test_answering.py tests/test_reference_intents.py tests/test_support_coordinator.py -k "hosted or provider or tool or boundary or clarify"
```

Expected: PASS

- [ ] **Step 4: Run the 2.1 gate regression**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_gap_intake.py tests/test_source_intake.py tests/test_dataset_export.py tests/test_factory_model.py tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py tests/test_answering.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_pilot_closed_loop.py tests/test_docs_contract.py tests/test_vendor_profiles.py tests/test_pack_runtime.py tests/test_doctor.py tests/test_support_coordinator.py tests/test_reference_intents.py tests/test_session_events.py
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/config.py src/sentieon_assist/llm_backends.py src/sentieon_assist/doctor.py src/sentieon_assist/runtime_guidance.py src/sentieon_assist/cli.py src/sentieon_assist/answering.py src/sentieon_assist/reference_intents.py src/sentieon_assist/support_coordinator.py tests/test_config.py tests/test_llm_backends.py tests/test_doctor.py tests/test_runtime_guidance.py tests/test_cli.py tests/test_answering.py tests/test_reference_intents.py tests/test_support_coordinator.py
git commit -m "feat: add internal hosted runtime poc"
```

## Code-Phase Entry Criteria

Code phase may begin once:

- this engineering plan is committed
- the revised spec package remains stable
- the branch is clean
- implementation starts from `Chunk 1`, not from the PoC

## Success Criteria

This plan succeeds when it gives the code phase a strict order of operations:

- hard governance contracts first
- provider capability layer second
- tool arbitration and boundary enforcement third
- eval/trace plane fourth
- minimal hosted runtime PoC last

At that point, `2.1` is ready to enter code phase without drifting into a full-RAG support bot.
