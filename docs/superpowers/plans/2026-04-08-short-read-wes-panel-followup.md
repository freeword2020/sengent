# Short-read WES/Panel Follow-up Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend deterministic local follow-up handling so `WES` / `panel` threads followed by short-read fragments such as `那短读长呢` or `那 short-read 呢` resolve to dedicated intermediate guidance blocks instead of overcommitting to germline WES or falling back to generic panel routing.

**Architecture:** Keep the current rule-first and workflow-guide-first architecture. Reuse existing local short-read canonicalization in `cli.py`, and add only the missing `short-read-wes` and `short-read-panel` entries to `workflow-guides.json`. Do not touch `external tools` or `files format` materials.

**Tech Stack:** Python 3.11, `pytest`, local JSON guide bundle in `sentieon-note/`, existing `sentieon_assist` CLI/chat pipeline

---

## Chunk 1: Lock The WES/Panel Short-read Gap With Failing Tests

### Task 1: Add red tests for short-read WES and panel follow-ups

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_answering.py`

- [x] **Step 1: Write failing CLI follow-up tests**

Add focused chat-loop tests for:
- `WES` context followed by `那 short-read 呢`
- `panel` context followed by `那短读长呢`

- [x] **Step 2: Write failing deterministic answer-path tests**

Add `answer_reference_query()` tests that assert:
- `WES + 那 short-read 呢` resolves to a dedicated short-read WES guidance block
- `panel + 那 short-read 呢` resolves to a dedicated short-read panel guidance block
- both stay narrower than generic workflow blocks but do not overcommit to germline/somatic before that branch is known

- [x] **Step 3: Run targeted tests to verify they fail for the right reason**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py -k "short_read_wes_panel_fragment_followup"
python3.11 -m pytest -q tests/test_answering.py -k "short_read_wes_panel_fragment_followup"
```

Expected:
- new tests fail because the current workflow bundle does not yet expose those intermediate short-read branches

## Chunk 2: Add Minimal Short-read WES/Panel Routing

### Task 2: Add dedicated workflow-guide entries

**Files:**
- Modify: `sentieon-note/workflow-guides.json`

- [x] **Step 1: Add `short-read-wes` and `short-read-panel` entries**

The new entries should:
- match `WES/panel` + `short-read/短读长`
- keep the answer at an intermediate branch
- continue asking for germline vs somatic, and then for germline whether DNAscope vs DNAseq conditions hold

- [x] **Step 2: Run targeted tests**

Run:

```bash
python3.11 -m json.tool sentieon-note/workflow-guides.json >/dev/null
python3.11 -m pytest -q tests/test_cli.py -k "short_read_wes_panel_fragment_followup or reference_context"
python3.11 -m pytest -q tests/test_answering.py -k "short_read_wes_panel_fragment_followup or workflow_guidance"
```

Expected:
- new tests pass
- existing workflow routing tests remain green

## Chunk 3: Docs Sync And Final Verification

### Task 3: Document the new short-read WES/panel follow-ups and verify the repo

**Files:**
- Modify: `README.md`
- Modify: `docs/project-context.md`

- [x] **Step 1: Sync docs**

Document that `WES` / `panel` short-read semantic follow-ups now resolve to dedicated intermediate guidance blocks.

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
python3.11 -m sentieon_assist.cli "我要做wes分析，能给个示例脚本吗 那 short-read 呢"
python3.11 -m sentieon_assist.cli "我要做panel分析，能给个示例脚本吗 那短读长呢"
```

Expected:
- both return deterministic `【流程指导】`
- no leaked Markdown markers
