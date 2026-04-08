# Hybrid Follow-up Routing Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep `hybrid` follow-up turns on the deterministic workflow-guidance path when they appear under an existing workflow context such as `WGS` or `long-read`, instead of jumping straight to the `DNAscope Hybrid` script/module answer.

**Architecture:** Keep the existing rule-first and workflow-guide-first architecture. Add the minimum local follow-up canonicalization in `cli.py` for `联合分析` / `short-read + long-read` fragments, teach `reference_intents.py` to prefer `workflow_guidance` for contextual hybrid follow-ups, and add a single dedicated `hybrid-analysis` entry to `workflow-guides.json`. Preserve the direct module-script path for standalone `DNAscope Hybrid` script requests.

**Tech Stack:** Python 3.11, `pytest`, local JSON guide bundle in `sentieon-note/`, existing `sentieon_assist` CLI/chat pipeline

---

## Chunk 1: Lock The Hybrid Follow-up Gap With Failing Tests

### Task 1: Add red tests for contextual hybrid follow-ups

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_reference_intents.py`

- [x] **Step 1: Write failing chat follow-up tests**

Add focused chat-loop tests for:
- `WGS` context followed by `那联合分析呢`
- `WGS` context followed by `那 short-read + long-read 呢`

- [x] **Step 2: Write failing parser/answer tests**

Add tests that assert:
- `parse_reference_intent("我要做wgs分析，能给个示例脚本吗 那 hybrid 呢")` returns `workflow_guidance`
- `parse_reference_intent("我要做long-read分析，能给个示例脚本吗 那 hybrid 呢")` returns `workflow_guidance`
- `answer_reference_query()` for those hybrid follow-ups returns `【流程指导】` rather than `【参考命令】`

- [x] **Step 3: Run targeted tests to verify they fail for the right reason**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py -k "hybrid_followup"
python3.11 -m pytest -q tests/test_reference_intents.py -k "hybrid_followup"
python3.11 -m pytest -q tests/test_answering.py -k "hybrid_followup"
```

Expected:
- new tests fail because contextual hybrid follow-ups still go through script/module routing or generic workflow blocks

## Chunk 2: Add Minimal Hybrid Workflow Routing

### Task 2: Canonicalize and route contextual hybrid follow-ups

**Files:**
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/reference_intents.py`
- Modify: `sentieon-note/workflow-guides.json`

- [x] **Step 1: Canonicalize local hybrid fragment variants**

Handle short follow-up forms such as:
- `那联合分析呢`
- `那 short-read + long-read 呢`

and normalize them to the same local hybrid follow-up form before routing.

- [x] **Step 2: Prefer workflow guidance for contextual hybrid follow-ups**

Only when the query already carries broader workflow context such as `WGS` / `WES` / `panel` / `long-read`, prefer `workflow_guidance` over `script_example` for `hybrid` follow-ups.

- [x] **Step 3: Add a dedicated `hybrid-analysis` workflow guide**

The new entry should:
- explain that hybrid is a short-read + long-read joint analysis branch
- point to `DNAscope Hybrid` as the workflow branch
- ask the next workflow questions rather than immediately dumping the command skeleton

- [x] **Step 4: Run targeted tests**

Run:

```bash
python3.11 -m json.tool sentieon-note/workflow-guides.json >/dev/null
python3.11 -m pytest -q tests/test_cli.py -k "hybrid_followup or reference_context"
python3.11 -m pytest -q tests/test_reference_intents.py -k "hybrid_followup"
python3.11 -m pytest -q tests/test_answering.py -k "hybrid_followup or workflow_guidance"
```

Expected:
- hybrid follow-up tests pass
- standalone direct `DNAscope Hybrid` script tests remain green

## Chunk 3: Docs Sync And Final Verification

### Task 3: Document the new hybrid follow-up rule and verify the repo

**Files:**
- Modify: `README.md`
- Modify: `docs/project-context.md`

- [x] **Step 1: Sync docs**

Document that contextual `hybrid` follow-ups now stay on the workflow-guidance path, while standalone `DNAscope Hybrid` script requests still go to deterministic script answers.

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
python3.11 -m sentieon_assist.cli "我要做wgs分析，能给个示例脚本吗 那 hybrid 呢"
python3.11 -m sentieon_assist.cli "我要做long-read分析，能给个示例脚本吗 那联合分析呢"
```

Expected:
- both return deterministic `【流程指导】`
- no leaked Markdown markers
