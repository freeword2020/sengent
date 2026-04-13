# Sengent 2.0 Support Experience Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first CLI-first support UX chunk so structured answers read like directed senior support guidance: current judgment first, next step visible, clarify replies easy to provide, while keeping runtime truth and evidence rules unchanged.

**Architecture:** Leave answer generation, routing, trace collection, and session logging unchanged. Add a presentation-layer support answer card that parses existing structured answers, derives safe next-step / clarify affordances, and is reused by both one-shot CLI output and chat answer rendering.

**Tech Stack:** Python 3.11, pytest, existing `chat_ui.py` / `cli.py` / `answer_contracts.py` runtime, Rich console rendering

---

## Scope Boundary

This phase implements the first complete chunk of the roadmap’s user support experience upgrade.

This phase explicitly includes:

- a support answer card parser / formatter
- clarify reply hints
- next-step visibility for structured support answers
- chat panel rendering updates
- one-shot CLI answer presentation updates
- focused docs and tests

This phase explicitly does **not** include:

- frontend UI/backend work
- new retrieval or resolver behavior
- fake tool traces or fake live operations
- automatic activation or online learning
- broad chat memory redesign

## File Map

- Create: `src/sentieon_assist/support_experience.py`
  - parse raw structured answers into presentation slots
  - derive safe next-step and clarify reply hints
  - render support answer card text for CLI/chat
- Modify: `src/sentieon_assist/chat_ui.py`
  - render answer cards instead of dumping raw structured text
- Modify: `src/sentieon_assist/cli.py`
  - reuse answer-card presentation for chat and one-shot CLI answers
- Create: `tests/test_support_experience.py`
  - parser / formatter behavior coverage
- Modify: `tests/test_chat_ui.py`
  - rendered answer card coverage
- Modify: `tests/test_cli.py`
  - one-shot CLI and chat presentation coverage
- Modify: `docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
  - only if support answer presentation changes operator wording materially

## Chunk 1: Lock The Presentation Contract

### Task 1: Write failing tests for answer-card behavior

**Files:**
- Create: `tests/test_support_experience.py`
- Modify: `tests/test_chat_ui.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add tests for structured answer parsing and rendering**

Add tests that prove:

- module / doc / troubleshooting answers render `current judgment` before evidence markers
- `【资料查询】` is de-emphasized into evidence instead of being the answer headline
- clarify answers expose both missing materials and a direct reply template
- module / parameter style answers gain safe next-step guidance when raw answer lacks explicit next steps

- [ ] **Step 2: Add CLI/chat presentation tests**

Add tests that prove:

- `ChatUI.render_answer()` displays the answer card presentation
- one-shot `main([...query...])` prints the formatted support answer card instead of raw artifact-like text
- stable raw response handling in `render_chat_response()` remains unchanged

- [ ] **Step 3: Run targeted tests to confirm failure**

Run:

```bash
python3.11 -m pytest -q tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py -k "support_experience or render_answer or support_card"
```

Expected: FAIL because the presentation layer does not exist yet.

## Chunk 2: Implement Support Answer Card MVP

### Task 2: Add the presentation layer and wire it into CLI/chat

**Files:**
- Create: `src/sentieon_assist/support_experience.py`
- Modify: `src/sentieon_assist/chat_ui.py`
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Implement structured answer parsing**

Parse sectioned answers into slots:

- current judgment
- next steps
- clarify requirements
- reply hint
- evidence basis
- boundary notes

- [ ] **Step 2: Implement safe derived affordances**

Derive:

- clarify reply templates from missing fields
- safe follow-up guidance for module / parameter / workflow / doc answers

Constraints:

- never invent evidence
- never mutate raw answer text used for traces
- never fake operations or environment inspection

- [ ] **Step 3: Implement presentation renderer**

Produce a compact support card text that:

- leads with current judgment
- keeps next steps explicit
- shows reply hints when clarification is needed
- keeps evidence visible but lower in the card

- [ ] **Step 4: Wire the renderer into chat and one-shot CLI**

Use the same presentation formatter in:

- `ChatUI.render_answer`
- direct CLI query output path

Keep:

- `render_chat_response()` stable-answer behavior
- session event raw response logging

- [ ] **Step 5: Run targeted tests to verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py -k "support_experience or render_answer or support_card"
```

Expected: PASS

## Chunk 3: Verification And Closeout

### Task 3: Fresh verification and commit

**Files:**
- Verify: `tests/test_support_experience.py`
- Verify: `tests/test_chat_ui.py`
- Verify: `tests/test_cli.py`
- Verify: `tests/test_answering.py`
- Verify: `tests/test_docs_contract.py`

- [ ] **Step 1: Run focused verification**

Run:

```bash
python3.11 -m pytest -q tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py tests/test_answering.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 2: Run broader regression verification**

Run:

```bash
python3.11 -m pytest -q tests/test_gap_review.py tests/test_gap_intake.py tests/test_source_intake.py tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py tests/test_answering.py tests/test_knowledge_build.py tests/test_incident_memory.py tests/test_pilot_closed_loop.py tests/test_docs_contract.py
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-13-sengent-2-0-support-experience-design.md docs/superpowers/plans/2026-04-13-sengent-2-0-support-experience.md src/sentieon_assist/support_experience.py src/sentieon_assist/chat_ui.py src/sentieon_assist/cli.py tests/test_support_experience.py tests/test_chat_ui.py tests/test_cli.py
git commit -m "feat: upgrade support answer presentation"
```
