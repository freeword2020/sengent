# Sengent 2.1 Chat Polish Trust Boundary Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining hosted runtime trust-boundary gap on the `chat polish` path without widening into provider-seam refactors.

**Architecture:** Reuse the existing runtime outbound policy layer. Add a dedicated `chat-polish-outbound-v1` helper, sanitize `query/raw_response` before prompt construction, and thread only a minimal trust-boundary summary back into the existing session turn event.

**Tech Stack:** Python 3.11, pytest, `cli.py`, `runtime_outbound_trust.py`, current session-event trace pipeline

---

## Red Lines

- No raw `query` or `raw_response` may flow into hosted chat-polish prompts.
- No change to runtime truth or answer-routing logic.
- No provider/gateway seam rewrite in this slice.
- No item-level outbound audit trail in this slice.

## File Map

- Create: none
- Modify: `src/sentieon_assist/runtime_outbound_trust.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `tests/test_runtime_outbound_trust.py`
- Modify: `tests/test_cli.py`

## Chunk 1: Lock The Chat-Polish Boundary In Tests

### Task 1: Add failing tests

**Files:**
- Modify: `tests/test_runtime_outbound_trust.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add policy-layer tests**

Cover:

- `chat-polish-outbound-v1` redacts path / email / secret-like text

- [ ] **Step 2: Add CLI integration tests**

Cover:

- normal chat-polish prompt does not contain raw sensitive values
- missing-info polish prompt does not contain raw sensitive values
- `chat_loop()` persists `chat-polish-outbound-v1` summary into session log

- [ ] **Step 3: Run focused tests and verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_runtime_outbound_trust.py tests/test_cli.py -k "chat_polish or outbound_trust"
```

Expected: FAIL until the runtime policy and chat-loop plumbing exist.

## Chunk 2: Implement The Chat-Polish Outbound Policy

### Task 2: Add `chat-polish-outbound-v1`

**Files:**
- Modify: `src/sentieon_assist/runtime_outbound_trust.py`

- [ ] **Step 1: Add policy helper**

Requirements:

- sanitize `query`
- sanitize `raw_response`
- return `TrustBoundaryResult`

- [ ] **Step 2: Run focused policy tests**

Run:

```bash
python3.11 -m pytest -q tests/test_runtime_outbound_trust.py -k "chat_polish or outbound_trust"
```

Expected: PASS

## Chunk 3: Rewire `render_chat_response()` And `chat_loop()`

### Task 3: Consume sanitized chat-polish context and persist summary

**Files:**
- Modify: `src/sentieon_assist/cli.py`

- [ ] **Step 1: Sanitize before prompt construction**

Requirements:

- `render_chat_response()` uses `chat-polish-outbound-v1`
- both normal polish and missing-info polish prompts consume sanitized values

- [ ] **Step 2: Thread minimal trust summary**

Requirements:

- `render_chat_response()` can expose `trust_boundary_summary`
- `chat_loop()` writes that summary into the existing turn event

- [ ] **Step 3: Run focused CLI regression**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py -k "chat_polish_trust_boundary or sanitizes_chat_polish_prompt or sanitizes_missing_info_polish_prompt"
```

Expected: PASS

## Chunk 4: Regression And Commit

### Task 4: Verify and commit

- [ ] **Step 1: Run slice regression**

```bash
python3.11 -m pytest -q tests/test_runtime_outbound_trust.py tests/test_cli.py -k "chat_polish or outbound_trust"
```

Expected: PASS

- [ ] **Step 2: Run full regression**

```bash
python3.11 -m pytest -q
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/sentieon_assist/runtime_outbound_trust.py src/sentieon_assist/cli.py tests/test_runtime_outbound_trust.py tests/test_cli.py docs/superpowers/specs/2026-04-13-sengent-2-1-chat-polish-trust-boundary-design.md docs/superpowers/plans/2026-04-13-sengent-2-1-chat-polish-trust-boundary.md
git commit -m "feat: harden chat polish trust boundary"
```
