# Sentieon Support System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-anchor `Sengent` as a conservative Sentieon technical support assistant by centralizing route ownership, introducing explicit support session state, and fixing precision regressions such as capability-question fallback and `AlignmentStat` misrouting.

**Architecture:** Add a single support coordinator that owns top-level route priority across troubleshooting, onboarding guidance, reference lookup, and capability explanation. Move chat follow-up reuse into structured session state instead of raw string heuristics, while keeping existing deterministic answer engines and `rich` UI output stable wherever they are already correct.

**Tech Stack:** Python 3.11, pytest, rich, local deterministic reference indices

---

## File Map

- Create: `src/sentieon_assist/support_state.py`
  - Structured session state and route/task type definitions for support turns.
- Create: `src/sentieon_assist/support_coordinator.py`
  - Single route contract, capability-question detection, chat follow-up planning, and support-task decisions.
- Modify: `src/sentieon_assist/cli.py`
  - Replace ad hoc chat context fields and top-level route branching with coordinator-driven flow.
- Modify: `src/sentieon_assist/answering.py`
  - Add deterministic capability explanation answer and support coordinator integration hooks.
- Modify: `src/sentieon_assist/module_index.py`
  - Tighten module/entity matching so exact module names and aliases beat family-level substring matches.
- Modify: `src/sentieon_assist/chat_events.py`
  - Add labels needed for new support task classes if status text requires them.
- Test: `tests/test_cli.py`
  - Route ownership, capability explanation, chat follow-up state transitions.
- Test: `tests/test_answering.py`
  - Support-route behavior and capability explanation rendering.
- Test: `tests/test_module_index.py`
  - New focused matcher regression tests if a dedicated file is warranted; otherwise extend existing answering/cli coverage.

## Chunk 1: Centralize Support Routing

### Task 1: Add failing route-selection tests for support tasks

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_answering.py`

- [ ] **Step 1: Write the failing tests**

Add focused tests for:

- broad capability prompts such as `你能做什么` and `你不是可以提供sentieon的功能吗`
- onboarding-guidance prompts that should not fall back to `other`
- direct route-order cases where troubleshooting must outrank reference phrasing

Example shape:

```python
def test_run_query_routes_capability_question_to_support_explanation():
    text = run_query("你能做什么")
    assert "我可以帮你做这些 Sentieon 技术支持工作" in text
    assert "当前 MVP 仅支持 license 和 install 问题" not in text
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_cli.py -k "capability or route"`
Expected: FAIL because the current system still falls back to the old MVP message or routes through fragmented logic.

- [ ] **Step 3: Add support route/state primitives**

Implement:

- `SupportTask` definitions in `src/sentieon_assist/support_state.py`
- `SupportSessionState` with:
  - active task
  - anchor query
  - confirmed facts
  - open clarification slots
  - last route reason
- coordinator decision objects in `src/sentieon_assist/support_coordinator.py`

- [ ] **Step 4: Implement a single top-level route decision function**

In `src/sentieon_assist/support_coordinator.py`, add a function that:

- detects troubleshooting first
- then onboarding guidance
- then reference lookup
- then capability explanation
- falls back to clarification rather than model-free guessing

Keep the first pass heuristic and deterministic. Do not introduce a new model dependency for route ownership.

- [ ] **Step 5: Add deterministic capability explanation output**

In `src/sentieon_assist/answering.py`, add a compact deterministic answer for broad capability questions. It should:

- explain the supported help types
- invite the user to provide concrete next-step information
- avoid claiming general open-ended Sentieon knowledge

- [ ] **Step 6: Run targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_cli.py -k "capability or route"`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tests/test_cli.py tests/test_answering.py src/sentieon_assist/support_state.py src/sentieon_assist/support_coordinator.py src/sentieon_assist/answering.py src/sentieon_assist/cli.py src/sentieon_assist/chat_events.py
git commit -m "feat: centralize support route selection"
```

## Chunk 2: Replace Ad Hoc Chat Context With Support Session State

### Task 2: Lock failing chat-state regressions before moving logic

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/support_coordinator.py`
- Modify: `src/sentieon_assist/support_state.py`

- [ ] **Step 1: Write the failing chat-state tests**

Add tests for:

- workflow clarification turns that refine the same support task without blind string concatenation
- explicit task switching from onboarding/reference into troubleshooting
- `/reset` clearing structured support state

Example shape:

```python
def test_chat_loop_switches_from_guidance_to_troubleshooting_without_reusing_old_anchor():
    ...
    assert seen_queries == [
        "能提供个 wes 参考脚本吗",
        "license 报错 ..."
    ]
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_cli.py -k "chat_loop and (state or switch or reset or capability)"`
Expected: FAIL because chat state is still encoded through `pending_query` and `reference_context_query`.

- [ ] **Step 3: Move chat follow-up planning into the coordinator**

Implement explicit chat-turn planning in `src/sentieon_assist/support_coordinator.py`:

- answer current clarification slots when the new turn fits the active task
- switch tasks when the new turn clearly starts a new troubleshooting/guidance/reference request
- reuse normalized anchor context only through explicit support state

- [ ] **Step 4: Simplify `cli.py` to coordinator-driven chat flow**

Update `src/sentieon_assist/cli.py` so `chat_loop()`:

- stores a `SupportSessionState`
- asks the coordinator how to interpret the incoming turn
- stops directly owning route precedence and raw context concatenation

Keep:

- model warmup
- UI rendering
- thinking/generation status behavior
- `/quit` and `/reset`

- [ ] **Step 5: Run targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_cli.py -k "chat_loop and (state or switch or reset or capability)"`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/test_cli.py src/sentieon_assist/cli.py src/sentieon_assist/support_coordinator.py src/sentieon_assist/support_state.py
git commit -m "refactor: move chat context into support state"
```

## Chunk 3: Harden Entity Resolution And Preserve Existing Coverage

### Task 3: Add failing precision tests for concrete module matching

**Files:**
- Modify: `tests/test_answering.py`
- Modify: `tests/test_cli.py`
- Modify: `src/sentieon_assist/module_index.py`
- Modify: `src/sentieon_assist/answering.py`

- [ ] **Step 1: Write the failing precision tests**

Add regressions for:

- `介绍下AlignmentStat`
- `介绍下AlignmentStat模块功能`
- capability questions that should stay out of reference fallback
- any current customer-language examples captured in this thread that expose route or entity drift

Example shape:

```python
def test_answer_reference_query_prefers_exact_alignmentstat_over_alignment_family(...):
    text = answer_reference_query("介绍下AlignmentStat", source_directory=str(tmp_path))
    assert "AlignmentStat" in text
    assert "Alignment：" not in text
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_answering.py -k "alignmentstat or capability"`
Expected: FAIL because the current matcher still prefers broad substring matches.

- [ ] **Step 3: Tighten matcher precedence in `module_index.py`**

Refine `match_module_entries()` so scoring prefers:

1. exact query-to-name/alias matches
2. token-boundary matches
3. broad family matches only when no concrete submodule matches

Keep the implementation deterministic and transparent.

- [ ] **Step 4: Verify reference answers remain stable**

Ensure the matcher change does not regress existing:

- module overview answers
- parameter lookup answers
- script example answers

Use targeted tests rather than speculative code changes.

- [ ] **Step 5: Run targeted regression buckets**

Run:

- `python3.11 -m pytest -q tests/test_answering.py -k "alignmentstat or capability or reference"`
- `python3.11 -m pytest -q tests/test_cli.py -k "route or chat_loop"`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/test_answering.py tests/test_cli.py src/sentieon_assist/module_index.py src/sentieon_assist/answering.py src/sentieon_assist/cli.py src/sentieon_assist/support_coordinator.py
git commit -m "fix: harden support entity routing"
```

## Final Verification

- [ ] **Step 1: Run the full test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS with no new failures

- [ ] **Step 2: Run manual smoke checks through the CLI**

Run:

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "你能做什么"
PYTHONPATH=src python3.11 -m sentieon_assist.cli "你不是可以提供sentieon的功能吗"
PYTHONPATH=src python3.11 -m sentieon_assist.cli "介绍下AlignmentStat"
PYTHONPATH=src python3.11 -m sentieon_assist.cli "能提供个wes参考脚本吗"
```

Expected:

- capability prompts explain supported Sentieon help types
- `AlignmentStat` no longer collapses into `Alignment`
- `wes` script request asks for missing workflow facts conservatively

- [ ] **Step 3: Re-read the spec and verify requirement coverage**

Checklist:

- single top-level route ownership exists
- structured support state replaces ad hoc chat context
- capability explanation path exists
- entity precision is tighter than before
- UI shape remains materially unchanged
