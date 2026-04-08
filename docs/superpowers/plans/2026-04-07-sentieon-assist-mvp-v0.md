# Sentieon Assist MVP v0 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline CLI harness for a local Sentieon technical-support assistant using the local Ollama HTTP API, with rule-first answering, missing-information gating, fixed answer templates, and portable site configuration.

**Architecture:** Create a small Python package with a CLI entrypoint, an Ollama client wrapper, a deterministic harness state machine, schema-validated extraction, and external JSON knowledge packs for `license` and `install` issues. Keep the deployed model id, Ollama base URL, and site-specific Sentieon knowledge files in configuration so the package can be installed at customer sites and updated for future Sentieon versions or model swaps without code changes.

**Tech Stack:** Python 3, `requests`, `pytest`, local Ollama HTTP API, JSON, flat files

---

## File Structure

- Create: `pyproject.toml`
- Create: `src/sentieon_assist/__init__.py`
- Create: `src/sentieon_assist/cli.py`
- Create: `src/sentieon_assist/ollama_client.py`
- Create: `src/sentieon_assist/prompts.py`
- Create: `src/sentieon_assist/models.py`
- Create: `src/sentieon_assist/classifier.py`
- Create: `src/sentieon_assist/config.py`
- Create: `src/sentieon_assist/extractor.py`
- Create: `src/sentieon_assist/state_machine.py`
- Create: `src/sentieon_assist/rules.py`
- Create: `src/sentieon_assist/answering.py`
- Create: `knowledge/base/license.json`
- Create: `knowledge/base/install.json`
- Create: `knowledge/README.md`
- Create: `tests/test_cli.py`
- Create: `tests/test_classifier.py`
- Create: `tests/test_config.py`
- Create: `tests/test_extractor.py`
- Create: `tests/test_state_machine.py`
- Create: `tests/test_rules.py`
- Create: `tests/test_answering.py`
- Create: `tests/test_integration_local.py`
- Create: `docs/local-ollama-environment.md`

## Chunk 1: Environment Prerequisite

### Task 1: Record the current local Ollama environment status

**Files:**
- Create: `docs/local-ollama-environment.md`

- [ ] **Step 1: Write the environment note**

Document:
- installed app version
- current shell CLI crash symptom
- local model manifests present
- current desktop app HTTP API behavior
- current `gemma4:e4b` HTTP generation success evidence
- deployment rule: the project must call the local Ollama HTTP API, not rely on the desktop GUI

- [ ] **Step 2: Verify the note matches current evidence**

Run: `test -f ~/.ollama/models/manifests/registry.ollama.ai/library/gemma4/e4b`
Expected: exit code `0`

- [ ] **Step 3: Record the current server availability check**

Run: `curl -sS http://127.0.0.1:11434/api/tags`
Expected: model JSON that includes `gemma4:e4b` when the desktop app server is running

## Chunk 2: Python Project Skeleton

### Task 2: Create package metadata and entrypoint

**Files:**
- Create: `pyproject.toml`
- Create: `src/sentieon_assist/__init__.py`
- Create: `src/sentieon_assist/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI test**

```python
from sentieon_assist.cli import main


def test_cli_requires_query(capsys):
    code = main([])
    out = capsys.readouterr().out
    assert code == 2
    assert "query is required" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -q`
Expected: FAIL with import or symbol errors

- [ ] **Step 3: Write the minimal CLI skeleton**

Implement `main(argv)` and a thin console entrypoint that accepts a free-text query.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -q`
Expected: PASS

## Chunk 3: Ollama Client and Prompt Contract

### Task 3: Add the local Ollama HTTP client wrapper

**Files:**
- Create: `src/sentieon_assist/ollama_client.py`
- Create: `src/sentieon_assist/config.py`
- Create: `src/sentieon_assist/prompts.py`
- Test: `tests/test_answering.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing client test**

```python
from sentieon_assist.ollama_client import build_generate_payload


def test_build_generate_payload_uses_configured_model():
    payload = build_generate_payload("gemma4:e4b", "hello")
    assert payload["model"] == "gemma4:e4b"
    assert payload["stream"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_answering.py -q`
Expected: FAIL with import error

- [ ] **Step 3: Write the minimal wrapper**

Implement:
- `build_generate_payload(model, prompt)`
- `generate(model, prompt, base_url="http://127.0.0.1:11434")`
- friendly error when the local server is unreachable
- site config loader for `OLLAMA_BASE_URL` and `OLLAMA_MODEL`

- [ ] **Step 4: Add the fixed answer template**

Template sections:
- `【问题判断】`
- `【可能原因】`
- `【建议步骤】`
- `【需要补充的信息】`

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_answering.py -q`
Expected: PASS

## Chunk 4: Classification and Extraction

### Task 4: Add `license` and `install` classification

**Files:**
- Create: `src/sentieon_assist/models.py`
- Create: `src/sentieon_assist/classifier.py`
- Test: `tests/test_classifier.py`

- [ ] **Step 1: Write failing classification tests**

```python
from sentieon_assist.classifier import normalize_issue_type


def test_normalize_issue_type_accepts_license():
    assert normalize_issue_type("license") == "license"


def test_normalize_issue_type_falls_back_to_other():
    assert normalize_issue_type("pipeline") == "other"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_classifier.py -q`
Expected: FAIL

- [ ] **Step 3: Implement the minimal classifier contract**

Support only:
- `license`
- `install`
- `other`

Everything outside the MVP scope must normalize to `other`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_classifier.py -q`
Expected: PASS

### Task 5: Add schema-validated extraction

**Files:**
- Create: `src/sentieon_assist/extractor.py`
- Test: `tests/test_extractor.py`

- [ ] **Step 1: Write failing extraction tests**

```python
from sentieon_assist.extractor import validate_extracted_info


def test_validate_extracted_info_fills_missing_keys():
    info = validate_extracted_info({"version": "202503"})
    assert info["version"] == "202503"
    assert info["error"] == ""
    assert info["step"] == ""
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_extractor.py -q`
Expected: FAIL

- [ ] **Step 3: Implement extraction validation**

Rules:
- accept only expected keys
- coerce missing keys to empty strings
- reject malformed non-dict JSON from the model
- surface extraction failure as structured error, not raw traceback

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_extractor.py -q`
Expected: PASS

## Chunk 5: Harness State Machine

### Task 6: Add the minimal state machine

**Files:**
- Create: `src/sentieon_assist/state_machine.py`
- Test: `tests/test_state_machine.py`

- [ ] **Step 1: Write failing state-machine tests**

```python
from sentieon_assist.state_machine import next_state


def test_missing_info_routes_to_need_info():
    assert next_state("EXTRACTED", has_missing_info=True) == "NEED_INFO"


def test_ready_routes_to_answered():
    assert next_state("READY", has_missing_info=False) == "ANSWERED"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_state_machine.py -q`
Expected: FAIL

- [ ] **Step 3: Implement the state machine**

Use:
- `RECEIVED`
- `CLASSIFIED`
- `EXTRACTED`
- `NEED_INFO`
- `READY`
- `ANSWERED`
- `ESCALATED`

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_state_machine.py -q`
Expected: PASS

## Chunk 6: Rule-First Answering

### Task 7: Add the initial external rule database

**Files:**
- Create: `src/sentieon_assist/rules.py`
- Create: `knowledge/base/license.json`
- Create: `knowledge/base/install.json`
- Create: `knowledge/README.md`
- Test: `tests/test_rules.py`

- [ ] **Step 1: Write failing rule-match tests**

```python
from sentieon_assist.rules import match_rule


def test_match_rule_finds_license_rule():
    rule = match_rule("license 报错，找不到 license 文件")
    assert rule is not None
    assert rule["category"] == "license"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_rules.py -q`
Expected: FAIL

- [ ] **Step 3: Implement minimal rule coverage**

Initial rule packs:
- 3 `license` cases
- 3 `install` cases

Rule payload must include:
- `category`
- `patterns`
- `causes`
- `steps`
- `requires`

The README must explain:
- how to add a new Sentieon version-specific rule pack
- how to swap models without code changes
- how a customer site can override the base knowledge files

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_rules.py -q`
Expected: PASS

### Task 8: Add answer formatting and fallback behavior

**Files:**
- Create: `src/sentieon_assist/answering.py`
- Test: `tests/test_answering.py`

- [ ] **Step 1: Write failing answer-format tests**

```python
from sentieon_assist.answering import format_rule_answer


def test_format_rule_answer_uses_required_sections():
    text = format_rule_answer(
        {
            "category": "license",
            "causes": ["环境变量未设置"],
            "steps": ["检查 SENTIEON_LICENSE"],
            "requires": ["Sentieon 版本"],
        }
    )
    assert "【问题判断】" in text
    assert "【可能原因】" in text
    assert "【建议步骤】" in text
    assert "【需要补充的信息】" in text
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_answering.py -q`
Expected: FAIL

- [ ] **Step 3: Implement rule-first answering**

Behavior:
- if rule matches and required info is present, answer from the rule
- if required info is missing, return missing-info prompt
- if issue type is `other`, return escalation guidance
- only call the model when rule coverage is insufficient and the issue type is in MVP scope

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_answering.py -q`
Expected: PASS

## Chunk 7: Local Integration Path

### Task 9: Wire the CLI to the harness flow

**Files:**
- Modify: `src/sentieon_assist/cli.py`
- Modify: `src/sentieon_assist/classifier.py`
- Modify: `src/sentieon_assist/extractor.py`
- Modify: `src/sentieon_assist/state_machine.py`
- Modify: `src/sentieon_assist/answering.py`
- Test: `tests/test_integration_local.py`

- [ ] **Step 1: Write the failing integration test**

```python
from sentieon_assist.cli import run_query


def test_license_query_without_version_requests_more_info():
    text = run_query("license 报错，无法激活")
    assert "需要补充以下信息" in text
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_integration_local.py -q`
Expected: FAIL

- [ ] **Step 3: Implement the end-to-end flow**

Flow:
- classify
- extract
- validate extracted fields
- compute missing fields
- answer from rules or escalate

- [ ] **Step 4: Run the full local suite**

Run: `pytest -q`
Expected: PASS

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-07-sentieon-assist-mvp-v0.md`. Ready to execute?
