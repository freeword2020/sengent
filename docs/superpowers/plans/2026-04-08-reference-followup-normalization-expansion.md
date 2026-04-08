# Reference Follow-up Normalization Expansion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand deterministic local follow-up handling so short reference continuations along input-shape and platform axes resolve from local rules and indexed workflow guides instead of falling back to the model.

**Architecture:** Keep the current rule-first and workflow-guide-first architecture. Extend the local follow-up normalizer in `cli.py` so high-signal short fragments are canonicalized before routing, then add the minimum context-specific entries to `workflow-guides.json` so the existing deterministic answer path can answer them without redesigning chat or the answer formatter. Preserve the current “vague deictic follow-up does not auto-reuse context” boundary.

**Tech Stack:** Python 3.11, `pytest`, local JSON guide bundle in `sentieon-note/`, existing `sentieon_assist` CLI/chat pipeline

---

## Chunk 1: Lock Input-Shape And Platform Follow-up Scope With Failing Tests

### Task 1: Add red tests for the next deterministic follow-up families

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_answering.py`

- [x] **Step 1: Write failing CLI follow-up tests for short normalized fragments**

Add focused chat-loop tests for:
- `WGS/WES/panel` context followed by `那 FASTQ 呢`
- `WGS/WES/panel` context followed by `那 BAM 呢`
- `long-read` context followed by `那 ONT 呢`
- `long-read` context followed by `那 HiFi 呢`

Test shape:

```python
def test_chat_loop_carries_reference_context_for_fastq_fragment_followup(monkeypatch):
    ...
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 fastq 呢"]
```

- [x] **Step 2: Write failing deterministic answer-path tests for the same families**

Add `answer_reference_query()` tests that assert:
- `FASTQ/BAM` follow-ups land on context-specific guidance rather than generic workflow blocks
- `ONT/HiFi` follow-ups land on context-specific long-read guidance
- stable displayed answers remain compact and do not expose `【资料查询】`

- [x] **Step 3: Run the targeted tests to verify they fail for the right reason**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py -k "fastq_fragment or bam_fragment or ont_fragment or hifi_fragment"
python3.11 -m pytest -q tests/test_answering.py -k "fastq_fragment_followup or bam_fragment_followup or ont_fragment_followup or hifi_fragment_followup"
```

Expected:
- new tests fail because the current normalizer / workflow bundle does not yet cover these follow-up axes
- existing follow-up tests remain green

## Chunk 2: Extend The Indexed Workflow Guide Bundle

### Task 2: Add context-specific deterministic guide entries for normalized fragments

**Files:**
- Modify: `sentieon-note/workflow-guides.json`
- Modify: `sentieon-note/README.md`

- [x] **Step 1: Add the minimum new guide entries**

Extend `workflow-guides.json` with stable entries for:
- input-shape follow-ups where the parent workflow is already determined:
  - `wgs-fastq-input`
  - `wgs-bam-cram-input`
  - `wes-fastq-input`
  - `wes-bam-cram-input`
  - `panel-fastq-input`
  - `panel-bam-cram-input`
- long-read platform follow-ups:
  - `long-read-hifi`
  - `long-read-ont`

Keep the same field shape as existing entries:

```json
{
  "id": "wgs-fastq-input",
  "name": "WGS FASTQ input",
  "priority": 0,
  "require_any_groups": [],
  "exclude_any": [],
  "prefer_any": [],
  "summary": "...",
  "guidance": [],
  "prerequisites": [],
  "follow_up": [],
  "sources": []
}
```

- [x] **Step 2: Sanity-check the JSON before touching Python**

Run:

```bash
python3.11 -m json.tool sentieon-note/workflow-guides.json >/dev/null
```

Expected:
- JSON validates

- [x] **Step 3: Update the note README with the new indexed follow-up axes**

Document that the workflow guide bundle now carries deterministic follow-up coverage for:
- paired/unpaired somatic fragments
- input-shape fragments
- long-read platform fragments

## Chunk 3: Normalize And Route The New Follow-up Fragments

### Task 3: Extend local follow-up classification without redesigning chat

**Files:**
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/reference_intents.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_answering.py`

- [x] **Step 1: Normalize new high-signal short fragments locally**

Extend the local follow-up normalizer in `cli.py` so fragments like:
- `那 FASTQ 呢`
- `那 BAM 呢`
- `那 CRAM 呢`
- `那 ONT 呢`
- `那 HiFi 呢`

canonicalize before routing, without calling the model.

- [x] **Step 2: Keep vague deictics blocked**

Do not re-open context reuse for inputs like:
- `那这个输入呢`
- `这个平台呢`
- `那这个格式呢`

unless they also contain a high-signal deterministic cue that the local rules already recognize.

- [x] **Step 3: Run targeted follow-up tests**

Run:

```bash
python3.11 -m pytest -q tests/test_cli.py -k "reference_context or run_query_routes"
python3.11 -m pytest -q tests/test_answering.py -k "workflow_guidance or normalize_model_answer"
```

Expected:
- new input/platform follow-up tests pass
- existing follow-up and stable-display tests remain green

## Chunk 4: Docs Sync And Final Verification

### Task 4: Document the expanded follow-up rule set and verify the repo

**Files:**
- Modify: `README.md`
- Modify: `docs/project-context.md`
- Modify: `sentieon-note/README.md`

- [x] **Step 1: Sync docs**

Document that deterministic follow-up normalization now covers:
- paired/unpaired somatic fragments across `WGS/WES/panel`
- input-shape follow-ups such as `FASTQ/BAM/CRAM`
- long-read platform follow-ups such as `ONT/HiFi`
- the remaining non-goal: vague deictic follow-ups still do not auto-reuse context

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
python3.11 -m sentieon_assist.cli "我要做wgs分析，能给个示例脚本吗 那 FASTQ 呢"
python3.11 -m sentieon_assist.cli "我要做long-read分析，能给个示例脚本吗 那 ONT 呢"
```

Expected:
- both return deterministic `【流程指导】`
- no leaked Markdown markers
- no model dependency for the follow-up recognition itself
