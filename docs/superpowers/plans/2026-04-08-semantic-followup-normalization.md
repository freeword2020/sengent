# Semantic Follow-up Normalization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend deterministic local follow-up handling for short semantic fragments such as `那体细胞呢` and `那胚系呢` so `WES` / `panel` workflow threads stay on the rule-first path without falling back to the model or collapsing back to generic workflow blocks.

**Architecture:** Keep the existing rule-first and workflow-guide-first architecture. Extend the local follow-up canonicalizer in `cli.py` for the smallest set of high-signal germline/somatic fragments, then add only the missing context-specific entries to `workflow-guides.json`. Do not touch `external tools` or `files format` source work already being handled in the parallel materials thread.

**Tech Stack:** Python 3.11, `pytest`, local JSON guide bundle in `sentieon-note/`, existing `sentieon_assist` CLI/chat pipeline

---

## Chunk 1: Lock Semantic Follow-up Scope With Failing Tests

### Task 1: Add red tests for germline/somatic short fragments

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_answering.py`

- [x] **Step 1: Write failing CLI follow-up tests for semantic fragments**

Add focused chat-loop tests for:
- `WES` context followed by `那体细胞呢`
- `panel` context followed by `那体细胞呢`
- `panel` context followed by `那胚系呢`

Prefer canonicalized assertions like:

```python
assert seen_queries == [
    "我要做wes分析，能给个示例脚本吗",
    "我要做wes分析，能给个示例脚本吗 那 somatic 呢",
]
```

- [x] **Step 2: Write failing deterministic answer-path tests for the same families**

Add `answer_reference_query()` tests that assert:
- `WES + 那 somatic 呢` resolves to a dedicated somatic-WES guidance block
- `panel + 那 somatic 呢` resolves to a dedicated somatic-panel guidance block
- `panel + 那 germline 呢` resolves to a dedicated germline-panel guidance block

- [x] **Step 3: Run the targeted tests to verify they fail for the right reason**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py -k "semantic_fragment_followup"
python3.11 -m pytest -q tests/test_answering.py -k "semantic_fragment_followup"
```

Expected:
- new tests fail because the current canonicalizer / workflow bundle does not yet cover these follow-up branches
- existing tests stay green

## Chunk 2: Add Minimal Semantic Follow-up Routing

### Task 2: Extend canonicalization and workflow guides

**Files:**
- Modify: `src/sentieon_assist/cli.py`
- Modify: `sentieon-note/workflow-guides.json`

- [x] **Step 1: Canonicalize the smallest useful semantic fragments locally**

Handle short forms such as:
- `那体细胞呢`
- `那肿瘤的呢`
- `那胚系呢`

Canonicalize them before routing, in the same spirit as existing paired/unpaired follow-up normalization.

- [x] **Step 2: Add only the missing workflow-guide entries**

Extend `workflow-guides.json` with stable entries for:
- `somatic-wes`
- `somatic-panel`
- `germline-panel`

Reuse existing compact workflow-guidance sections; do not add a new answer format.

- [x] **Step 3: Run targeted follow-up tests**

Run:

```bash
python3.11 -m json.tool sentieon-note/workflow-guides.json >/dev/null
python3.11 -m pytest -q tests/test_cli.py -k "semantic_fragment_followup or reference_context"
python3.11 -m pytest -q tests/test_answering.py -k "semantic_fragment_followup or workflow_guidance"
```

Expected:
- new semantic follow-up tests pass
- existing deterministic workflow tests remain green

## Chunk 3: Docs Sync And Final Verification

### Task 3: Document the new semantic follow-up layer and verify the repo

**Files:**
- Modify: `README.md`
- Modify: `docs/project-context.md`

- [x] **Step 1: Sync docs**

Document that deterministic follow-up normalization now also covers semantic
germline/somatic fragments in workflow contexts, while still excluding vague
deictic fragments and not overlapping the parallel `external tools` / `files format`
materials expansion.

- [x] **Step 2: Run the full suite**

Run:

```bash
python3.11 -m pytest -q
```

Expected:
- full suite passes

- [x] **Step 3: Run real CLI smokes**

Run:

```bash
cd /Users/zhuge/Documents/codex/harness
export PYTHONPATH=src
python3.11 -m sentieon_assist.cli "我要做wes分析，能给个示例脚本吗 那体细胞呢"
python3.11 -m sentieon_assist.cli "我要做panel分析，能给个示例脚本吗 那胚系呢"
```

Expected:
- both return deterministic `【流程指导】`
- no leaked Markdown markers
- no model dependency for the follow-up recognition itself
