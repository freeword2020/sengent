# NotebookLM Adversarial Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the 50 NotebookLM adversarial prompts into a conservative regression set that strengthens support routing and prevents unsupported deep-dive hallucinations.

**Architecture:** Add a deterministic reference-boundary path for unsupported benchmark/comparison/mechanism prompts, store the 50 prompts as structured adversarial data, and expand the subprocess drill to use that corpus while preserving existing supported lookup behavior.

**Tech Stack:** Python 3.11, pytest, local JSON fixtures, CLI subprocess drill

---

## File Map

- Create: `tests/data/notebooklm_adversarial_cases.json`
  - Structured 50-prompt audit and expected drill behavior.
- Modify: `src/sentieon_assist/answering.py`
  - Detect unsupported deep-dive reference prompts and emit deterministic boundary answers.
- Modify: `tests/test_answering.py`
  - Boundary regressions and supported-answer preservation.
- Modify: `tests/test_cli.py`
  - CLI-level regression for boundary answers.
- Modify: `scripts/adversarial_support_drill.py`
  - Load and run the expanded corpus through fresh subprocesses.

## Chunk 1: Audit Corpus and Boundary Tests

### Task 1: Add the adversarial corpus and failing regressions

**Files:**
- Create: `tests/data/notebooklm_adversarial_cases.json`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add the structured adversarial corpus**

Create a JSON file with all 50 prompts and for each item include:

- `id`
- `prompt`
- `expected_mode`
- `audit_bucket`

- [ ] **Step 2: Write failing boundary tests**

Add tests for prompts such as:

- cloud cost / benchmark claims
- competitive comparison claims
- roadmap / future graph-size claims
- mixed deep-dive prompts that currently fall through to model fallback

Expected shape:

```python
def test_answer_reference_query_returns_boundary_for_benchmark_claim(...):
    text = answer_reference_query("为什么在 AWS 上成本可以压到 1~5 美元？", ...)
    assert "【资料边界】" in text
```

- [ ] **Step 3: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_answering.py -k "boundary or benchmark or roadmap"`
Expected: FAIL because the current system still tries to synthesize unsupported reference answers.

## Chunk 2: Deterministic Boundary Path

### Task 2: Implement conservative unsupported-reference handling

**Files:**
- Modify: `src/sentieon_assist/answering.py`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add boundary detection helpers**

Detect unsupported reference prompts using conservative cues such as:

- benchmark / speedup / cost / exact numeric claims
- competitive comparisons
- roadmap / future-looking sample-count questions
- deep mechanism prompts that fall outside structured module/parameter/workflow coverage

- [ ] **Step 2: Add a deterministic boundary formatter**

Return a stable `【资料边界】` answer that:

- explains why the system should not answer confidently
- states the supported help boundary
- suggests a narrower support-safe follow-up

- [ ] **Step 3: Route unsupported prompts to the boundary formatter**

Integrate this before model fallback so unsupported prompts no longer use free-form synthesis.

- [ ] **Step 4: Run targeted tests to verify they pass**

Run:

- `python3.11 -m pytest -q tests/test_answering.py -k "boundary or benchmark or roadmap"`
- `python3.11 -m pytest -q tests/test_cli.py -k "boundary or benchmark or roadmap"`

Expected: PASS

## Chunk 3: Expanded Subprocess Drill

### Task 3: Load the corpus into the independent drill

**Files:**
- Modify: `scripts/adversarial_support_drill.py`
- Modify: `tests/data/notebooklm_adversarial_cases.json`

- [ ] **Step 1: Replace hard-coded cases with JSON-backed loading**

Load the corpus file and preserve per-case expectations.

- [ ] **Step 2: Keep fresh subprocess execution**

Run each case via a fresh CLI subprocess so state is isolated.

- [ ] **Step 3: Run the drill manually**

Run: `python3.11 scripts/adversarial_support_drill.py`
Expected: PASS for the committed corpus.

## Final Verification

- [ ] **Step 1: Run focused tests**

Run:

- `python3.11 -m pytest -q tests/test_answering.py`
- `python3.11 -m pytest -q tests/test_cli.py`

- [ ] **Step 2: Run the full suite**

Run: `python3.11 -m pytest -q`

- [ ] **Step 3: Run the expanded adversarial drill**

Run: `python3.11 scripts/adversarial_support_drill.py`

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-08-notebooklm-adversarial-hardening-design.md docs/superpowers/plans/2026-04-08-notebooklm-adversarial-hardening.md tests/data/notebooklm_adversarial_cases.json tests/test_answering.py tests/test_cli.py src/sentieon_assist/answering.py scripts/adversarial_support_drill.py
git commit -m "feat: harden support against adversarial reference prompts"
```
