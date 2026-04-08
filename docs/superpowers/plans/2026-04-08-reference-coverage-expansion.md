# Milestone 10 Reference Coverage Expansion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand deterministic local-reference coverage so more Sentieon module, parameter, global-option, and script questions resolve from the mounted source bundle before falling back to slow model synthesis.

**Architecture:** Keep the existing rule-first and module-index-first architecture. Extend the structured source bundle first, then teach the existing reference intent parser and answer formatters how to route more queries into deterministic answer builders. Do not redesign the chat shell in this phase; only touch chat behavior where deterministic answers need new routing or display-safe formatting.

**Tech Stack:** Python 3.11, `pytest`, local JSON/Markdown source bundle in `sentieon-note/`, existing `sentieon_assist` CLI/chat pipeline

---

## Chunk 1: Lock Scope With Failing Tests

### Task 1: Add deterministic-coverage tests for new reference targets

**Files:**
- Modify: `tests/test_answering.py`
- Modify: `tests/test_reference_intents.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing answer-path tests for the next deterministic targets**

Add focused tests for:
- `sentieon-cli` common global options such as `-t` or `-r`
- `GeneEditEvaluator` module intro and script/reference-command coverage
- cross-turn follow-up queries that rely on a previous reference answer

Example test shape:

```python
def test_answer_reference_query_returns_global_option_answer(tmp_path):
    text = answer_reference_query("--algo 是什么", source_directory=str(tmp_path))
    assert "【常用参数】" in text
    assert "--algo" in text
```

- [ ] **Step 2: Run the targeted tests to verify they fail for the right reason**

Run:

```bash
pytest -q tests/test_answering.py -k "global_option or gene_edit"
pytest -q tests/test_reference_intents.py -k "global_option or gene_edit"
pytest -q tests/test_cli.py -k "reference_context"
```

Expected:
- new tests fail because the current source bundle / routing does not yet cover them deterministically
- existing tests stay green

- [ ] **Step 3: Tighten expected output contracts before implementation**

Adjust assertions so they verify:
- deterministic answers stay in compact `【模块介绍】` or `【常用参数】` form
- no raw Markdown markers leak into displayed stable answers
- follow-up turns reuse prior reference context only when the short follow-up is clearly reference-related

- [ ] **Step 4: Re-run the same targeted tests**

Run:

```bash
pytest -q tests/test_answering.py -k "global_option or gene_edit"
pytest -q tests/test_reference_intents.py -k "global_option or gene_edit"
pytest -q tests/test_cli.py -k "reference_context"
```

Expected:
- all new tests still fail
- failure messages now point at missing deterministic coverage rather than vague assertions

- [ ] **Step 5: Commit**

```bash
git add tests/test_answering.py tests/test_reference_intents.py tests/test_cli.py
git commit -m "test: lock next reference coverage targets"
```

## Chunk 2: Expand the Structured Source Bundle

### Task 2: Add the next deterministic reference entries to the mounted notes

**Files:**
- Modify: `sentieon-note/sentieon-modules.json`
- Modify: `sentieon-note/sentieon-module-index.md`
- Modify: `sentieon-note/sentieon-script-index.md`
- Modify: `sentieon-note/README.md`

- [ ] **Step 1: Add missing structured entries for the chosen next targets**

Extend `sentieon-modules.json` with stable fields for:
- `GeneEditEvaluator`
- chosen `sentieon-cli` common global options
- any shared script metadata needed for deterministic script answers

Keep field shapes consistent with the existing schema:

```json
{
  "name": "GeneEditEvaluator",
  "summary": "…",
  "scope": ["…"],
  "inputs": ["…"],
  "outputs": ["…"],
  "parameters": [],
  "script_examples": []
}
```

- [ ] **Step 2: Update the human-readable indexes**

Refresh:
- `sentieon-module-index.md` so a human can confirm the new module coverage
- `sentieon-script-index.md` so script/index coverage matches the structured JSON
- `sentieon-note/README.md` so future threads know which files now back these answers

- [ ] **Step 3: Sanity-check the data shape before touching Python**

Run:

```bash
python3.11 -m json.tool sentieon-note/sentieon-modules.json >/dev/null
pytest -q tests/test_sources.py
```

Expected:
- JSON validates
- source/index smoke tests stay green

- [ ] **Step 4: Commit**

```bash
git add sentieon-note/sentieon-modules.json sentieon-note/sentieon-module-index.md sentieon-note/sentieon-script-index.md sentieon-note/README.md tests/test_sources.py
git commit -m "feat: expand deterministic Sentieon reference bundle"
```

## Chunk 3: Route More Queries Into Deterministic Answers

### Task 3: Extend intent parsing and answer builders for the new bundle entries

**Files:**
- Modify: `src/sentieon_assist/reference_intents.py`
- Modify: `src/sentieon_assist/prompts.py`
- Modify: `src/sentieon_assist/module_index.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/cli.py`
- Test: `tests/test_answering.py`
- Test: `tests/test_reference_intents.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Make the intent parser distinguish the new query families**

Add the minimal intent / heuristic coverage needed for:
- global-option lookups
- `GeneEditEvaluator` intro and script-example requests
- short reference follow-ups that should reuse the previous module context

- [ ] **Step 2: Run the intent tests to confirm they still fail only on implementation gaps**

Run:

```bash
pytest -q tests/test_reference_intents.py -k "global_option or gene_edit"
```

Expected:
- tests fail because routing/normalization is not implemented yet

- [ ] **Step 3: Implement minimal deterministic answer builders**

Teach the existing module-index path to return stable answers for the new entries:
- compact `【模块介绍】` for module intros
- compact `【常用参数】` for parameter / global-option explanations
- `【参考命令】` blocks for script skeletons

Do not add new answer shapes unless the existing compact sections are clearly insufficient.

- [ ] **Step 4: Wire chat/CLI routing without redesigning the shell**

Only update `cli.py` where needed so the new deterministic answers:
- route through `run_query()` cleanly
- remain stable in chat
- preserve current Markdown cleanup and `正在思考中...` behavior

- [ ] **Step 5: Run the targeted tests**

Run:

```bash
pytest -q tests/test_answering.py -k "global_option or gene_edit or normalize_model_answer"
pytest -q tests/test_reference_intents.py
pytest -q tests/test_cli.py -k "reference_context or stable_markdown or run_query_routes"
```

Expected:
- targeted tests pass
- no regression in existing deterministic reference paths

- [ ] **Step 6: Commit**

```bash
git add src/sentieon_assist/reference_intents.py src/sentieon_assist/prompts.py src/sentieon_assist/module_index.py src/sentieon_assist/answering.py src/sentieon_assist/cli.py tests/test_answering.py tests/test_reference_intents.py tests/test_cli.py
git commit -m "feat: expand deterministic reference routing"
```

## Chunk 4: Final Verification and Handoff

### Task 4: Re-sync docs and verify the repo after implementation

**Files:**
- Modify: `README.md`
- Modify: `docs/project-context.md`
- Modify: `sentieon-note/README.md`

- [ ] **Step 1: Update user-facing docs for the new coverage**

Document:
- newly supported deterministic module/script/global-option queries
- any newly indexed modules or script skeletons
- any operator-visible limitations that still remain

- [ ] **Step 2: Run the full suite**

Run:

```bash
pytest -q
```

Expected:
- full suite passes

- [ ] **Step 3: Run one real chat smoke**

Run:

```bash
cd /Users/zhuge/Documents/codex/harness
export PYTHONPATH=src
python3.11 -m sentieon_assist chat
```

Then try:
- `sentieon-cli 的 -t 是什么`
- `GeneEditEvaluator 是做什么的`
- `能给个 geneeditevaluator 的参考脚本吗`

Expected:
- prompt remains `Sengent>`
- chat still shows `正在思考中...`
- deterministic answers return without leaked Markdown markers

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project-context.md sentieon-note/README.md
git commit -m "docs: sync expanded reference coverage"
```
