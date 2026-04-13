# Sengent 2.1 Hosted-LLM Architecture Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Sengent from an Ollama-first runtime assumption to a hosted-LLM-ready, provider-aware runtime contract while preserving 2.0 governance, active-knowledge truth boundaries, and rollback discipline.

**Architecture:** Keep `Support Kernel + Knowledge Compiler + Knowledge Factory + Deterministic Diagnostics` intact. Introduce a canonical provider-aware runtime adapter contract first, then upgrade diagnostics/operator surfaces, and only after that plan factory-side hosted drafting. Runtime remains bounded by active knowledge and answer contracts throughout.

**Tech Stack:** Python 3.11, pytest, existing `llm_backends.py` OpenAI-compatible transport, current CLI/runtime modules, 2.0 vendor profile / pack runtime / factory draft infrastructure

---

## Scope Boundary

This plan covers the first formal `2.1` tranche.

It explicitly includes:

- `2.1` architecture/anti-drift documentation
- provider-aware runtime config contract
- provider-aware backend-router primary selection
- compatibility mapping from current Ollama-first env vars
- provider-aware diagnostics planning
- isolated `2.1` branch/worktree execution

It explicitly excludes:

- raw-doc retrieval as runtime truth
- model outputs directly mutating active packs
- auto-activate
- second vendor rollout
- multi-tenant gateway
- full runtime prompt strategy rewrite
- factory remote-provider integration in this first implementation chunk

## Control Surfaces That Must Stay Intact

- active knowledge remains the runtime truth source
- build / review / gate / activate / rollback remain mandatory
- clarify-first remains stronger than retrieval breadth
- deterministic diagnostics remain first-class
- gap capture / offline learning loop remain intact
- vendor/domain/playbook/incident layering remains explicit

## File Map

### Documentation

- Add: `docs/superpowers/specs/2026-04-13-sengent-2-1-hosted-llm-architecture-design.md`
- Add: `docs/superpowers/architecture/2026-04-13-sengent-2-1-anti-drift-principles.md`
- Add: `docs/superpowers/plans/2026-04-13-sengent-2-1-hosted-llm-architecture.md`

### Chunk 1 Files

- Modify: `src/sentieon_assist/config.py`
  - canonical runtime provider config
  - compatibility alias mapping from current env vars
- Modify: `src/sentieon_assist/llm_backends.py`
  - provider-aware primary backend construction
  - keep `ollama` and `openai_compatible` runtime providers
- Modify: `tests/test_config.py`
  - canonical env tests
  - compatibility alias tests
- Modify: `tests/test_llm_backends.py`
  - provider-aware router tests

### Later Chunks

- Modify later: `src/sentieon_assist/doctor.py`
- Modify later: `src/sentieon_assist/runtime_guidance.py`
- Modify later: `src/sentieon_assist/cli.py`
- Modify later: `tests/test_doctor.py`
- Modify later: `tests/test_runtime_guidance.py`
- Modify later: `tests/test_cli.py`
- Modify later: `src/sentieon_assist/factory_model.py`

## Phase 0: Publish 2.0 And Isolate 2.1

- [x] Push `codex/sengent-2.0` to GitHub and establish tracking
- [x] Create isolated `codex/sengent-2.1` worktree
- [x] Fast-forward `codex/sengent-2.1` onto the `2.0` baseline

## Phase 1: Lock The 2.1 Architecture Contract

### Task 1: Add the design/plan docs before implementation

**Files:**
- Add documentation files listed above

- [x] **Step 1: Write hosted-LLM architecture design**

Must capture:

- product definition
- non-goals
- current Ollama-first audit
- target layer diagram in prose
- first implementation slice

- [x] **Step 2: Write anti-drift principles**

Must capture:

- raw-retrieval red line
- model outputs are drafts, never truth
- knowledge layering stays explicit
- rollback discipline

- [x] **Step 3: Write the execution plan**

Must capture:

- phased rollout
- file map
- chunk boundaries
- verification commands

## Phase 2: Canonical Runtime Provider Contract

### Task 2: Add failing tests for provider-aware runtime config

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_llm_backends.py`

- [ ] **Step 1: Add config tests for canonical runtime env vars**

Cover:

- `SENGENT_RUNTIME_LLM_PROVIDER`
- `SENGENT_RUNTIME_LLM_BASE_URL`
- `SENGENT_RUNTIME_LLM_MODEL`
- `SENGENT_RUNTIME_LLM_API_KEY`
- `SENGENT_RUNTIME_LLM_KEEP_ALIVE`

Expected behavior:

- `openai_compatible` can be configured as the primary runtime provider
- `ollama` remains a supported provider

- [ ] **Step 2: Add compatibility tests for legacy env mapping**

Cover:

- `OLLAMA_*` still map into the canonical runtime contract when canonical vars are absent
- existing `SENGENT_LLM_FALLBACK_*` behavior does not regress unless intentionally superseded

- [ ] **Step 3: Add router tests for provider-aware primary selection**

Cover:

- router primary becomes `OpenAICompatibleBackend` when canonical provider is `openai_compatible`
- router primary remains `OllamaBackend` when canonical provider is `ollama`
- unknown providers fail clearly

- [ ] **Step 4: Run focused tests and confirm they fail first**

Run:

```bash
python3.11 -m pytest -q tests/test_config.py tests/test_llm_backends.py
```

Expected: FAIL because the canonical provider contract does not exist yet.

### Task 3: Implement the canonical runtime provider contract

**Files:**
- Modify: `src/sentieon_assist/config.py`
- Modify: `src/sentieon_assist/llm_backends.py`

- [ ] **Step 1: Add canonical runtime LLM fields to `AppConfig`**

At minimum:

- `runtime_llm_provider`
- `runtime_llm_base_url`
- `runtime_llm_model`
- `runtime_llm_api_key`
- `runtime_llm_keep_alive`

Requirements:

- canonical fields load from new env vars first
- legacy Ollama vars remain supported as aliases
- default behavior remains compatible with current local setup

- [ ] **Step 2: Rebuild `build_backend_router()` around the canonical runtime fields**

Requirements:

- canonical provider drives primary backend construction
- support `ollama` and `openai_compatible`
- do not remove fallback support yet unless the tests deliberately redefine it
- unknown providers fail with a clear error

- [ ] **Step 3: Keep current runtime call sites unchanged**

This chunk should not yet rewrite:

- `answering.py`
- `reference_intents.py`
- `cli.py`

Those callers should continue using `build_backend_router(load_config())` unchanged.

- [ ] **Step 4: Run focused tests and confirm pass**

Run:

```bash
python3.11 -m pytest -q tests/test_config.py tests/test_llm_backends.py
```

Expected: PASS

## Phase 3: Provider-Aware Diagnostics And Operator Contract

### Task 4: Generalize doctor/runtime guidance without changing truth semantics

**Files:**
- Modify later: `src/sentieon_assist/doctor.py`
- Modify later: `src/sentieon_assist/runtime_guidance.py`
- Modify later: `src/sentieon_assist/cli.py`
- Modify later: `tests/test_doctor.py`
- Modify later: `tests/test_runtime_guidance.py`
- Modify later: `tests/test_cli.py`

- [ ] **Step 1: Add failing tests for provider-aware diagnostics**

Cover:

- doctor reports the configured runtime provider, base URL, and model
- hosted providers do not emit `ollama pull` guidance
- build-only guidance remains available

- [ ] **Step 2: Implement provider-aware report shape**

Requirements:

- doctor no longer depends on an `ollama`-named payload shape internally
- current managed-pack/source health checks remain intact
- `--skip-ollama` can remain as a compatibility option in this tranche if needed

- [ ] **Step 3: Implement provider-aware runtime error guidance**

Requirements:

- local-provider guidance stays actionable
- hosted-provider guidance focuses on credentials/config reachability
- no raw-retrieval or truth-path wording changes

- [ ] **Step 4: Run focused diagnostics tests**

Run:

```bash
python3.11 -m pytest -q tests/test_doctor.py tests/test_runtime_guidance.py tests/test_cli.py -k "doctor or runtime_error or skip_ollama"
```

Expected: PASS

## Phase 4: Hosted Runtime PoC Regression

### Task 5: Prove the hosted-first contract does not break 2.0 control surfaces

**Files:**
- Verify only

- [ ] **Step 1: Run focused runtime regression**

Run:

```bash
python3.11 -m pytest -q tests/test_answering.py tests/test_reference_intents.py tests/test_cli.py -k "answer or reference or capability"
```

- [ ] **Step 2: Run docs contract**

Run:

```bash
python3.11 -m pytest -q tests/test_docs_contract.py
```

- [ ] **Step 3: Run broader 2.0 control-surface regression**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_gap_intake.py tests/test_source_intake.py tests/test_dataset_export.py tests/test_factory_model.py tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py tests/test_answering.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_pilot_closed_loop.py tests/test_docs_contract.py tests/test_vendor_profiles.py tests/test_pack_runtime.py tests/test_doctor.py tests/test_support_coordinator.py
```

Expected: PASS

## Phase 5: Factory-Side Hosted Adapter Preparation

### Task 6: Plan, but do not yet implement, hosted factory transport

**Files:**
- Modify later: `src/sentieon_assist/factory_model.py`
- Modify later: factory-model design/plan docs

- [ ] **Step 1: Define factory-specific provider config and audit fields**

Must preserve:

- offline-only execution
- review-required draft status
- source reference provenance
- template provenance

- [ ] **Step 2: Ensure runtime and factory adapters stay semantically separate**

Do not unify them around a shared “truth” abstraction.

Shared transport seam is allowed.

## Execution Order

The immediate next execution chunk is only:

1. `tests/test_config.py`
2. `tests/test_llm_backends.py`
3. `src/sentieon_assist/config.py`
4. `src/sentieon_assist/llm_backends.py`

Nothing else should be changed in the first implementation pass unless a tightly-coupled test fix is unavoidable.

## Handoff Notes For The Worker

- keep `2.0` governance unchanged
- do not touch runtime truth path
- do not touch active packs
- do not add remote provider SDK coupling
- do not start factory remote-provider integration yet
- prefer TDD: failing tests first, then implementation, then focused regression
