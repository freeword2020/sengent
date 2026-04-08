# Short-read WGS Follow-up Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend deterministic local follow-up handling so `WGS` threads followed by short-read fragments such as `那短读长呢` or `那 short-read 呢` resolve to a dedicated short-read WGS guidance block instead of falling back to the generic WGS ambiguity answer.

**Architecture:** Keep the current rule-first and workflow-guide-first architecture. Add the minimum local canonicalization in `cli.py` for short-read semantic fragments, then add a single context-specific `short-read-wgs` entry to `workflow-guides.json`. Do not touch `external tools` or `files format` materials.

**Tech Stack:** Python 3.11, `pytest`, local JSON guide bundle in `sentieon-note/`, existing `sentieon_assist` CLI/chat pipeline

---

## Chunk 1: Lock The Short-read WGS Gap With Failing Tests

### Task 1: Add red tests for short-read WGS semantic follow-up

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_answering.py`

- [x] **Step 1: Write failing CLI follow-up tests**

Add a focused chat-loop test for:
- `WGS` context followed by `那短读长呢`

Prefer a canonicalized assertion:

```python
assert seen_queries == [
    "我要做wgs分析，能给个示例脚本吗",
    "我要做wgs分析，能给个示例脚本吗 那 short-read 呢",
]
```

- [x] **Step 2: Write failing deterministic answer-path tests**

Add an `answer_reference_query()` test that asserts:
- `WGS + 那 short-read 呢` resolves to a dedicated short-read WGS guidance block
- the answer is narrower than generic `WGS` and no longer foregrounds long-read or pangenome branches

- [x] **Step 3: Run targeted tests to verify they fail for the right reason**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py -k "short_read_wgs_fragment_followup"
python3.11 -m pytest -q tests/test_answering.py -k "short_read_wgs_fragment_followup"
```

Expected:
- new tests fail because short-read WGS follow-up routing does not yet exist

## Chunk 2: Add Minimal Short-read WGS Routing

### Task 2: Canonicalize short-read follow-ups and add one workflow guide

**Files:**
- Modify: `src/sentieon_assist/cli.py`
- Modify: `sentieon-note/workflow-guides.json`

- [x] **Step 1: Canonicalize short-read fragments locally**

Handle:
- `那短读长呢`
- `那 short-read 呢`

and normalize them to the same local follow-up form before routing.

- [x] **Step 2: Add a dedicated `short-read-wgs` workflow entry**

The new entry should:
- match `WGS` + `short-read/短读长`
- explain the short-read WGS split without collapsing back to long-read or pangenome
- continue asking whether the case is germline vs somatic, and for germline whether the sample is diploid

- [x] **Step 3: Run targeted tests**

Run:

```bash
python3.11 -m json.tool sentieon-note/workflow-guides.json >/dev/null
python3.11 -m pytest -q tests/test_cli.py -k "short_read_wgs_fragment_followup or reference_context"
python3.11 -m pytest -q tests/test_answering.py -k "short_read_wgs_fragment_followup or workflow_guidance"
```

Expected:
- new short-read WGS follow-up tests pass
- existing deterministic workflow tests remain green

## Chunk 3: Docs Sync And Final Verification

### Task 3: Document the new short-read WGS follow-up and verify the repo

**Files:**
- Modify: `README.md`
- Modify: `docs/project-context.md`

- [x] **Step 1: Sync docs**

Document that short-read semantic follow-ups under `WGS` now resolve to a dedicated intermediate workflow guidance block.

- [x] **Step 2: Run the full suite**

Run:

```bash
python3.11 -m pytest -q
```

Expected:
- full suite passes

- [x] **Step 3: Run a real CLI smoke**

Run:

```bash
cd /Users/zhuge/Documents/codex/harness
export PYTHONPATH=src
python3.11 -m sentieon_assist.cli "我要做wgs分析，能给个示例脚本吗 那短读长呢"
```

Expected:
- returns deterministic `【流程指导】`
- no leaked Markdown markers
