# Sentieon Module Index Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a stable structured module index so module-intro and common input/output questions are answered from curated Sentieon metadata before falling back to raw source search.

**Architecture:** Store a curated module index in the mounted source bundle under `sentieon-note/`, load it through a dedicated `module_index.py` helper, and route reference questions through index-first matching. Keep the existing source-search path as a fallback and as evidence for parameter-style questions.

**Tech Stack:** Python 3.11, pytest, local JSON source bundle, existing source-backed reference answer flow

---

### Task 1: Add the curated module index files

**Files:**
- Create: `sentieon-note/sentieon-modules.json`
- Create: `sentieon-note/sentieon-module-index.md`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- module intro queries like `dnascope是什么` to be answerable from a JSON index
- module input queries like `DNAscope 支持什么输入` to surface curated input fields

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_answering.py tests/test_classifier.py -k 'module_index or cnvscope or dnascope' -v`
Expected: FAIL because no module index loader or deterministic answer path exists yet

- [ ] **Step 3: Create the curated index**

Write the first stable JSON index with the approved core Sentieon modules and a matching Markdown overview grouped by category.

- [ ] **Step 4: Run tests to verify index-dependent fixtures load**

Run: `pytest tests/test_answering.py -k 'module_index' -v`
Expected: still FAIL until routing code is added

- [ ] **Step 5: Commit**

```bash
git add sentieon-note/sentieon-modules.json sentieon-note/sentieon-module-index.md
git commit -m "feat: add curated Sentieon module index data"
```

### Task 2: Add module index loading and matching

**Files:**
- Create: `src/sentieon_assist/module_index.py`
- Test: `tests/test_answering.py`

- [ ] **Step 1: Write the failing test**

Add tests for:
- matching `dnascope是什么`
- matching `CNVscope 是什么`
- preferring the longest alias when both family and child modules could match

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_answering.py -k 'module_index' -v`
Expected: FAIL with import or behavior mismatch

- [ ] **Step 3: Write minimal implementation**

Implement:
- JSON loader
- alias matcher
- query intent detector
- deterministic formatter for intro/input/output/related queries

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_answering.py -k 'module_index' -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/module_index.py tests/test_answering.py
git commit -m "feat: add Sentieon module index loader"
```

### Task 3: Route reference answers through the module index

**Files:**
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/classifier.py`
- Modify: `src/sentieon_assist/sources.py`
- Test: `tests/test_classifier.py`
- Test: `tests/test_sources.py`

- [ ] **Step 1: Write the failing test**

Add tests that require:
- `CNVscope 是什么` to be recognized as a reference query
- parameter questions to keep using source evidence when needed
- source bundle search to still work after adding module-index files

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_classifier.py tests/test_sources.py tests/test_answering.py -k 'reference or module_index' -v`
Expected: FAIL because classifier coverage and routing are incomplete

- [ ] **Step 3: Write minimal implementation**

Update the reference-query path so:
- direct module-intro style questions return deterministic indexed answers
- parameter-style questions prepend module-index evidence, then keep source search fallback
- generic source search retains the earlier retrieval-quality fixes

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_classifier.py tests/test_sources.py tests/test_answering.py -k 'reference or module_index' -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/answering.py src/sentieon_assist/classifier.py src/sentieon_assist/sources.py tests/test_classifier.py tests/test_sources.py tests/test_answering.py
git commit -m "feat: route Sentieon reference answers through module index"
```

### Task 4: Update operator-facing docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project-context.md`

- [ ] **Step 1: Write the failing check**

Document the new files and runtime behavior expected for module-intro queries.

- [ ] **Step 2: Run doc sanity check**

Run: `rg -n "module index|sentieon-modules.json|sentieon-module-index.md" README.md docs/project-context.md`
Expected: no matches before update

- [ ] **Step 3: Write minimal documentation**

Update repo docs to reflect:
- the new index files
- the new index-first reference answer path
- the fact that parameter answers still use source evidence

- [ ] **Step 4: Run doc sanity check again**

Run: `rg -n "module index|sentieon-modules.json|sentieon-module-index.md" README.md docs/project-context.md`
Expected: matches in both files

- [ ] **Step 5: Commit**

```bash
git add README.md docs/project-context.md
git commit -m "docs: describe Sentieon module index"
```

Plan complete and saved to `docs/superpowers/plans/2026-04-08-sentieon-module-index.md`. Ready to execute?
