# Sengent 2.1 Post-PoC Hardening Roadmap Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry `Sengent 2.1` from the current internal hosted-runtime PoC to the full pre-human-test enhancement layer, including offline `factory / GPT` industry-knowledge learning, while keeping runtime truth governance intact.

**Architecture:** `2.1` remains `LLM-native, but governance-first`. The runtime track and the factory-learning track advance in parallel, but with a hard boundary: runtime stays on active knowledge, deterministic diagnostics, and explicit boundaries; factory learning stays offline, review-only, and never promotes model output directly into truth. The finish line is a stable internal branch that is ready for structured human testing across both hosted runtime behavior and hosted factory-assisted learning, without entering customer packaging or raw-retrieval drift.

**Tech Stack:** Python 3.11, pytest, current `sentieon_assist` CLI/runtime/compiler/factory modules, OpenAI-compatible hosted provider surfaces, local JSON/JSONL artifacts, session-event traces, build/review/gate/activate workflow, existing factory draft artifacts

---

## Finish Line

This roadmap ends only when all of the following are true:

1. hosted runtime provider seams are hardened beyond the current PoC
2. outbound trust-boundary behavior is reviewable through eval/review/export surfaces
3. hosted factory drafting can use GPT/OpenAI-compatible APIs offline under explicit trust-boundary governance
4. at least one bounded `industry knowledge learning` path exists in factory as `draft -> review-needed -> maintainer review`, not as runtime truth
5. runtime + factory paths pass a pre-human-test verification gate and operator checklist

## Red Lines

- No raw ingestion enters runtime truth directly.
- No model output bypasses `build / review / gate / activate`.
- No factory learning path auto-activates packs.
- No runtime path turns into raw-retrieval support.
- No chunk mixes runtime truth plumbing with hosted factory learning.
- No chunk assumes `OpenAI-compatible` means provider capabilities are identical.

## Explicit Non-Goals

This roadmap does **not** include:

- customer packaging / distribution
- multi-tenant gateway platformization
- second vendor rollout
- active-pack auto-promotion
- online learning that changes runtime truth directly
- full RAG retrieval expansion

## Execution Rule

Execution order is fixed:

1. `runtime provider seam hardening`
2. `runtime trust-boundary audit trail`
3. `factory hosted adapter + factory trust boundary`
4. `offline GPT industry-knowledge learning pilot`
5. `pre-human-test smoke gate`

Do not skip ahead. In particular, do not start hosted factory learning until the runtime/provider trust seams are hardened.

## Frozen Control Surfaces

The following remain frozen unless a chunk explicitly says otherwise:

- active knowledge as runtime truth
- build / review / gate / activate / rollback
- vendor/domain/playbook/incident layering
- clarify-first
- deterministic diagnostics as first-class control plane
- factory output as `draft` until promoted

## Chunk 1: Runtime Provider Seam Hardening

**Intent:** Move the hosted runtime from “sanitized callsites with prompt-string backends” to a stricter provider-neutral outbound request seam that remains prompt-opaque at transport time and future-safe for gateways.

### Task 1: Lock the provider-neutral outbound request contract in tests

**Files:**
- Create: `src/sentieon_assist/llm_requests.py`
- Modify: `tests/test_llm_backends.py`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_reference_intents.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add failing backend contract tests**

Cover:

- backends accept a structured outbound request object instead of raw prompt-only callers
- outbound request carries purpose and trust-boundary metadata
- transport serialization stays provider-specific, but request construction stays provider-neutral

- [ ] **Step 2: Add failing caller integration tests**

Cover:

- troubleshooting fallback paths can issue structured outbound requests
- reference-intent path can issue structured outbound requests
- chat-polish path can issue structured outbound requests

- [ ] **Step 3: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_llm_backends.py tests/test_answering.py tests/test_reference_intents.py tests/test_cli.py -k "request_contract or outbound_request or provider_seam"
```

Expected: FAIL because callers and backends still speak mostly raw prompt strings.

### Task 2: Implement the provider-neutral outbound request seam

**Files:**
- Create: `src/sentieon_assist/llm_requests.py`
- Modify: `src/sentieon_assist/llm_backends.py`
- Modify: `src/sentieon_assist/runtime_outbound_trust.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/reference_intents.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Add outbound request dataclass helpers**

Include:

- request purpose / transport mode
- sanitized prompt payload
- trust-boundary summary attachment
- optional streaming flag

- [ ] **Step 2: Rewire runtime callsites**

Requirements:

- support/reference/reference-intent/chat-polish all build request objects
- backends receive request objects and serialize them per provider
- backend transport does not need to know how sanitization happened

- [ ] **Step 3: Run focused regression**

Run:

```bash
python3.11 -m pytest -q tests/test_llm_backends.py tests/test_answering.py tests/test_reference_intents.py tests/test_cli.py -k "request_contract or outbound_request or provider_seam"
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/sentieon_assist/llm_requests.py src/sentieon_assist/llm_backends.py src/sentieon_assist/runtime_outbound_trust.py src/sentieon_assist/answering.py src/sentieon_assist/reference_intents.py src/sentieon_assist/cli.py tests/test_llm_backends.py tests/test_answering.py tests/test_reference_intents.py tests/test_cli.py
git commit -m "refactor: harden hosted runtime provider seam"
```

## Chunk 2: Runtime Trust-Boundary Audit Trail

**Intent:** Make outbound safety behavior reviewable. The current system records summary counts, but maintainers still need a clearer audit/review/export view before stable human testing.

### Task 3: Add failing eval/review/export tests for outbound audit data

**Files:**
- Modify: `tests/test_session_events.py`
- Modify: `tests/test_eval_trace_plane.py`
- Modify: `tests/test_dataset_export.py`
- Modify: `tests/test_gap_review.py`
- Modify: `tests/test_knowledge_review.py`

- [ ] **Step 1: Add failing session/eval tests**

Cover:

- session events can carry redacted/provenance-only outbound audit items
- eval trace can expose outbound policy presence and redaction posture beyond counts

- [ ] **Step 2: Add failing review/export tests**

Cover:

- reviewed datasets preserve outbound safety metadata
- maintainer queue / review text can surface outbound audit details without leaking raw values

- [ ] **Step 3: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_session_events.py tests/test_eval_trace_plane.py tests/test_dataset_export.py tests/test_gap_review.py tests/test_knowledge_review.py -k "outbound_audit or trust_boundary_audit or eval_trace"
```

Expected: FAIL because the current review plane is still mostly summary-level.

### Task 4: Implement outbound audit trail propagation

**Files:**
- Modify: `src/sentieon_assist/session_events.py`
- Modify: `src/sentieon_assist/eval_trace_plane.py`
- Modify: `src/sentieon_assist/dataset_export.py`
- Modify: `src/sentieon_assist/gap_review.py`
- Modify: `src/sentieon_assist/knowledge_review.py`

- [ ] **Step 1: Persist redacted/provenance-only outbound audit items**

- [ ] **Step 2: Project them into eval/review/export surfaces**

- [ ] **Step 3: Run focused regression**

Run:

```bash
python3.11 -m pytest -q tests/test_session_events.py tests/test_eval_trace_plane.py tests/test_dataset_export.py tests/test_gap_review.py tests/test_knowledge_review.py -k "outbound_audit or trust_boundary_audit or eval_trace"
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/sentieon_assist/session_events.py src/sentieon_assist/eval_trace_plane.py src/sentieon_assist/dataset_export.py src/sentieon_assist/gap_review.py src/sentieon_assist/knowledge_review.py tests/test_session_events.py tests/test_eval_trace_plane.py tests/test_dataset_export.py tests/test_gap_review.py tests/test_knowledge_review.py
git commit -m "feat: add outbound audit trail review surfaces"
```

## Chunk 3: Factory Hosted Adapter + Factory Trust Boundary

**Intent:** Add the hosted provider seam to `Knowledge Factory`, but keep it isolated from runtime and governed by factory-specific trust-boundary rules.

### Task 5: Add failing hosted-factory contract tests

**Files:**
- Create: `src/sentieon_assist/factory_outbound_trust.py`
- Create: `src/sentieon_assist/factory_backends.py`
- Modify: `src/sentieon_assist/config.py`
- Modify: `src/sentieon_assist/factory_model.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_factory_model.py`

- [ ] **Step 1: Add failing config tests**

Cover:

- factory provider/base_url/api_key/model are separate from runtime provider settings
- factory provider can be disabled without affecting runtime provider

- [ ] **Step 2: Add failing factory-model tests**

Cover:

- factory draft can use a hosted adapter
- hosted factory request still returns `review-needed` draft artifacts only
- factory outbound trust boundary redacts local-only path/material as configured

- [ ] **Step 3: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_config.py tests/test_factory_model.py -k "factory_provider or factory_hosted or factory_trust_boundary"
```

Expected: FAIL because factory still only has the stub adapter.

### Task 6: Implement hosted factory adapter seam

**Files:**
- Create: `src/sentieon_assist/factory_outbound_trust.py`
- Create: `src/sentieon_assist/factory_backends.py`
- Modify: `src/sentieon_assist/config.py`
- Modify: `src/sentieon_assist/factory_model.py`
- Modify: `src/sentieon_assist/doctor.py`

- [ ] **Step 1: Add separate factory provider config surface**

- [ ] **Step 2: Add factory hosted adapter and trust-boundary preflight**

- [ ] **Step 3: Keep all outputs review-only**

Requirements:

- lifecycle remains `review-needed`
- no change to active packs
- no build auto-consumption

- [ ] **Step 4: Run focused regression**

Run:

```bash
python3.11 -m pytest -q tests/test_config.py tests/test_factory_model.py tests/test_doctor.py -k "factory_provider or factory_hosted or factory_trust_boundary"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/factory_outbound_trust.py src/sentieon_assist/factory_backends.py src/sentieon_assist/config.py src/sentieon_assist/factory_model.py src/sentieon_assist/doctor.py tests/test_config.py tests/test_factory_model.py tests/test_doctor.py
git commit -m "feat: add hosted factory adapter seam"
```

## Chunk 4: Offline GPT Industry-Knowledge Learning Pilot

**Intent:** Add a narrow, explicit `industry knowledge learning` path in the factory layer so hosted GPT can help draft vendor/domain/playbook knowledge candidates offline, but only as maintainer-reviewed artifacts.

### Task 7: Lock the first learning scope in tests

**Files:**
- Modify: `src/sentieon_assist/factory_model.py`
- Modify: `src/sentieon_assist/knowledge_review.py`
- Modify: `tests/test_factory_model.py`
- Modify: `tests/test_knowledge_review.py`

- [ ] **Step 1: Add failing learning-pilot tests**

Cover:

- one bounded learning scope is supported first:
  - `candidate_draft`
  - `incident_normalization`
  - `contradiction_cluster`
  - `dataset_draft`
- hosted adapter outputs remain `factory_model_draft`
- maintainer queue can distinguish hosted-learning drafts from stub drafts

- [ ] **Step 2: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_factory_model.py tests/test_knowledge_review.py -k "hosted_learning or learning_pilot or factory_model_draft"
```

Expected: FAIL because there is no explicit hosted-learning pilot contract yet.

### Task 8: Implement the first hosted-learning pilot

**Files:**
- Modify: `src/sentieon_assist/factory_model.py`
- Modify: `src/sentieon_assist/knowledge_review.py`
- Modify: `src/sentieon_assist/dataset_export.py`
- Modify: `src/sentieon_assist/gap_review.py`

- [ ] **Step 1: Mark hosted-learning artifacts explicitly**

Include:

- adapter/provider provenance
- task kind
- review hints
- trust-boundary provenance

- [ ] **Step 2: Keep maintainers in control**

Requirements:

- queue shows why the artifact exists
- review surfaces remain inspect-only unless a later explicit review action is added
- no artifact reaches active knowledge automatically

- [ ] **Step 3: Make learning drafts feed evaluation assets, not truth**

Requirements:

- dataset export can include hosted-learning provenance
- gap review can align learning outputs with eval expectations where relevant

- [ ] **Step 4: Run focused regression**

Run:

```bash
python3.11 -m pytest -q tests/test_factory_model.py tests/test_knowledge_review.py tests/test_dataset_export.py tests/test_gap_review.py -k "hosted_learning or learning_pilot or factory_model_draft"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/factory_model.py src/sentieon_assist/knowledge_review.py src/sentieon_assist/dataset_export.py src/sentieon_assist/gap_review.py tests/test_factory_model.py tests/test_knowledge_review.py tests/test_dataset_export.py tests/test_gap_review.py
git commit -m "feat: add hosted factory learning pilot"
```

## Chunk 5: Pre-Human-Test Smoke Gate

**Intent:** Freeze the branch at the point where both hosted runtime and hosted factory learning are stable enough for structured human testing.

### Task 9: Add the operator-facing pre-test gate

**Files:**
- Create: `docs/superpowers/operators/2026-04-13-sengent-2-1-pre-human-test-gate.md`
- Modify: `tests/test_docs_contract.py`

- [ ] **Step 1: Document the pre-test gate**

Must cover:

- runtime provider env/config
- factory provider env/config
- doctor checks
- prohibited operations
- expected review-only behavior for factory drafts
- manual test categories

- [ ] **Step 2: Run docs contract**

Run:

```bash
python3.11 -m pytest -q tests/test_docs_contract.py
```

Expected: PASS

### Task 10: Run the final verification gate

**Files:**
- No new files

- [ ] **Step 1: Run factory/runtime focused regression**

```bash
python3.11 -m pytest -q tests/test_config.py tests/test_llm_backends.py tests/test_doctor.py tests/test_runtime_guidance.py tests/test_cli.py tests/test_answering.py tests/test_reference_intents.py tests/test_support_coordinator.py tests/test_session_events.py tests/test_eval_trace_plane.py tests/test_factory_model.py tests/test_knowledge_review.py tests/test_dataset_export.py tests/test_gap_review.py -k "provider or trust or boundary or factory or hosted or eval"
```

Expected: PASS

- [ ] **Step 2: Run full regression**

```bash
python3.11 -m pytest -q
```

Expected: PASS

- [ ] **Step 3: If real provider credentials exist, run live smoke**

```bash
PYTHONPATH=src python3.11 -m sentieon_assist doctor
PYTHONPATH=src python3.11 -m sentieon_assist chat
PYTHONPATH=src python3.11 -m sentieon_assist knowledge factory-draft --help
```

Expected:

- runtime provider reachable or clear provider-specific remediation
- factory provider configured separately from runtime
- factory draft remains review-only

- [ ] **Step 4: Commit the gate docs if needed**

```bash
git add docs/superpowers/operators/2026-04-13-sengent-2-1-pre-human-test-gate.md tests/test_docs_contract.py
git commit -m "docs: add 2.1 pre-human-test gate"
```

## Exit Criteria

This roadmap is complete only when:

1. runtime hosted calls use a hardened provider-neutral seam
2. outbound audit data is visible enough for review/eval/export
3. factory hosted GPT integration exists but stays offline and review-only
4. one bounded industry-knowledge learning pilot works through maintainer review
5. the branch is ready for structured human testing, but has not drifted into runtime learning or raw retrieval
