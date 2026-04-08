# High-Frequency Error Association Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the deterministic high-frequency format/tool error-association layer so Sentieon assistant can route common VCF/BAM/CRAM/reference/interval/tooling error questions to stable, official-material-backed guidance instead of guessing or falling back to module lists.

**Architecture:** Build on the existing secondary reference layer that already separates Sentieon official workflow/module answers from external format/tool references. Keep machine-readable routing in `sentieon-note/*.json`, keep human-readable provenance in `sentieon-note/*reference.md`, and teach the existing reference answer path to prefer error associations only for clearly error-like queries. Do not let this work contaminate Sentieon workflow selection or module/parameter answers.

**Tech Stack:** Python 3.11, `pytest`, local JSON/Markdown source bundle in `sentieon-note/`, existing `sentieon_assist` reference pipeline (`reference_intents.py`, `answering.py`, `sources.py`, `external_guides.py`)

---

## Chunk 1: Lock the Remaining Coverage With Failing Tests

### Task 1: Add failing answer-path tests for the next high-frequency error families

**Files:**
- Modify: `tests/test_answering.py`
- Modify: `tests/test_sources.py`
- Modify: `tests/test_reference_intents.py`

- [ ] **Step 1: Add failing `answer_reference_query()` tests for the missing association families**

Add focused tests for at least these queries:
- contig naming / dictionary mismatch
- BED or interval coordinate-system mismatch
- FASTA / FAI / dict companion-file mismatch
- BAM sorting / indexing state mismatch
- non-error explanatory queries that must stay on the normal external guide path

Use explicit output contracts like:

```python
def test_checked_in_source_directory_exposes_contig_naming_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "VCF 报 contig not found 是什么情况",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.92),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "contig" in text.lower()
    assert "【优先检查】" in text
```

- [ ] **Step 2: Add negative tests that protect routing boundaries**

Add tests that confirm:
- `VCF 的 INFO 和 FORMAT 有什么区别` still returns `【资料说明】`, not `【关联判断】`
- `BAM 是什么格式` still returns the normal external format guide
- `如果我要做wgs分析，能不能给个指导` still stays on `workflow_guidance`

- [ ] **Step 3: Add source-selection tests for the new association family**

Extend `tests/test_sources.py` so external error-association sources:
- are included for clearly error-like external queries
- are not pulled into evidence for pure Sentieon workflow/module questions
- do not outrank normal external guides for non-error explanatory queries

- [ ] **Step 4: Run the targeted tests to confirm the new cases fail for the right reason**

Run:

```bash
pytest -q tests/test_answering.py -k "contig or bed or fasta or bam or external_error"
pytest -q tests/test_sources.py -k "external_error or external_reference"
pytest -q tests/test_reference_intents.py -k "reference_other or workflow_guidance"
```

Expected:
- new tests fail because the bundle or matcher does not yet cover these cases
- existing external-guide and workflow-guidance tests stay green

- [ ] **Step 5: Commit**

```bash
git add tests/test_answering.py tests/test_sources.py tests/test_reference_intents.py
git commit -m "test: lock high-frequency error association targets"
```

### Task 2: Add CLI-level regression coverage for stable rendering

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add a CLI routing test for one error-association query and one negative query**

Cover:
- an error-like query such as `BAM 报 read group 不一致怎么办`
- a non-error external query such as `FastQC 是做什么的`

Verify the CLI path preserves:
- compact stable formatting
- no leaked Markdown markers
- no fallback-only phrasing when a local deterministic association exists

- [ ] **Step 2: Run the targeted CLI tests**

Run:

```bash
pytest -q tests/test_cli.py -k "external or reference"
```

Expected:
- new CLI tests fail until the final routing/output contracts are in place

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: lock cli contracts for error associations"
```

## Chunk 2: Expand the Local Error-Association Bundle

### Task 3: Expand the machine-readable error-association index

**Files:**
- Modify: `sentieon-note/external-error-associations.json`
- Modify: `sentieon-note/external-format-guides.json`
- Modify: `sentieon-note/external-tool-guides.json`

- [ ] **Step 1: Add the next association entries to `external-error-associations.json`**

Add at least these entries:
- `contig-naming-mismatch`
- `bed-coordinate-system-mismatch`
- `reference-companion-files-mismatch`
- `bam-sort-or-index-state`

Use a stable entry shape. If the matcher needs richer constraints, draft the entries in the target schema now:

```json
{
  "id": "contig-naming-mismatch",
  "name": "Contig naming / sequence dictionary mismatch",
  "patterns_any": ["contig", "chr", "dictionary", "sequence", "not found", "mismatch"],
  "require_groups": [["报错", "失败", "异常", "not found", "mismatch", "incompatible"], ["contig", "chr", "dictionary", "sequence"]],
  "exclude_any": ["是什么", "格式", "区别"],
  "summary": "这更像是 contig 命名、顺序或 sequence dictionary 组织不一致的问题。",
  "checks": [
    "先确认 FASTA、FAI、dict、VCF/BAM/CRAM header 使用的是同一套 contig 名和顺序。",
    "再确认 chr 前缀、MT/M 这类命名差异是否在上下游混用。",
    "如果错误发生在 interval 或 region query，也要检查目标文件的 contig 是否真实存在。"
  ],
  "related_guides": ["FASTA/FAI", "VCF/BCF", "SAM/BAM/CRAM"],
  "usage_boundary": [
    "这是格式/参考一致性层关联判断，不直接替代具体业务结论。"
  ],
  "source_notes": ["external-error-reference.md"]
}
```

- [ ] **Step 2: Ensure related guide coverage exists for every new association**

Update external guide indexes so each new association points to an existing guide entry:
- `Sequence Dictionary (.dict)` or an expanded `FASTA/FAI` guide
- `BED / interval coordinate system`
- `BAM sorting and indexing`
- `contig naming / reference companion files`

If an existing guide already covers the topic, extend that entry instead of creating a duplicate.

- [ ] **Step 3: Keep usage boundaries explicit in every new JSON entry**

Every new entry must make these boundaries machine-readable:
- this is external format/tool evidence, not Sentieon workflow evidence
- if a question turns into Sentieon pipeline selection, route back to official manual/app notes
- if the local official material does not cover the final remediation step, say so explicitly

- [ ] **Step 4: Validate the JSON before touching Python**

Run:

```bash
python3.11 -m json.tool sentieon-note/external-error-associations.json >/dev/null
python3.11 -m json.tool sentieon-note/external-format-guides.json >/dev/null
python3.11 -m json.tool sentieon-note/external-tool-guides.json >/dev/null
```

Expected:
- all three files parse cleanly

- [ ] **Step 5: Commit**

```bash
git add sentieon-note/external-error-associations.json sentieon-note/external-format-guides.json sentieon-note/external-tool-guides.json
git commit -m "feat: expand high-frequency error association index"
```

### Task 4: Sync the human-readable provenance notes

**Files:**
- Modify: `sentieon-note/external-error-reference.md`
- Modify: `sentieon-note/external-format-reference.md`
- Modify: `sentieon-note/external-tool-reference.md`
- Modify: `sentieon-note/README.md`

- [ ] **Step 1: Expand `external-error-reference.md` with the same association families**

For each new family, record:
- the error shape in plain language
- why it maps to a format/tool layer
- which official source backs the checks
- what this note does not prove

- [ ] **Step 2: Sync supporting format/tool notes**

Update the format/tool reference files so a human reader can trace each new association back to:
- HTS specs for VCF/SAM/BAM/CRAM/BED-like semantics where applicable
- HTSlib / samtools / bcftools docs for sorting, indexing, faidx, tabix, region access, or header inspection behavior

Do not elevate community blogs or Chinese mirrors into the main source chain.

- [ ] **Step 3: Update `sentieon-note/README.md` with the new quick-lookup categories**

Add bullets for:
- contig naming / dictionary mismatch
- BED coordinate mismatch
- FASTA / FAI / dict companion mismatch
- BAM sorting / indexing state

- [ ] **Step 4: Commit**

```bash
git add sentieon-note/external-error-reference.md sentieon-note/external-format-reference.md sentieon-note/external-tool-reference.md sentieon-note/README.md
git commit -m "docs: sync external error association provenance"
```

## Chunk 3: Harden Matcher Semantics and Routing

### Task 5: Upgrade the external error-association matcher so it can distinguish true error queries

**Files:**
- Modify: `src/sentieon_assist/external_guides.py`
- Test: `tests/test_answering.py`

- [ ] **Step 1: Add the minimal richer matcher primitives**

Extend the matcher to support optional fields like:
- `exclude_any`
- `require_groups`

Keep the implementation small and local. A minimal helper shape is enough:

```python
def _matches_groups(normalized_query: str, groups: list[list[str]]) -> bool:
    if not groups:
        return True
    return all(any(term in normalized_query for term in group) for group in groups)
```

Do not add a full rule engine.

- [ ] **Step 2: Apply the richer matcher only where it reduces real false positives**

Use the extra fields to keep these boundaries stable:
- `VCF 的 INFO 和 FORMAT 有什么区别` should not trigger an error association
- `BED 是什么格式` should not trigger an error association
- `CRAM 解码时报 reference mismatch 怎么看` should trigger an error association

- [ ] **Step 3: Re-run the targeted answer-path tests**

Run:

```bash
pytest -q tests/test_answering.py -k "contig or bed or fasta or bam or external_error or fastqc or vcf"
```

Expected:
- the new error-association tests now pass
- previously implemented external-guide tests remain green

- [ ] **Step 4: Commit**

```bash
git add src/sentieon_assist/external_guides.py tests/test_answering.py
git commit -m "feat: harden external error association matching"
```

### Task 6: Keep router precedence and source inclusion deterministic

**Files:**
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/sources.py`
- Modify: `src/sentieon_assist/reference_intents.py`
- Test: `tests/test_sources.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Keep precedence explicit in `answer_reference_query()`**

Maintain this order:
1. workflow guidance
2. external error association for clearly error-like external queries
3. normal external guide
4. module / parameter / script routing

Do not let the new layer short-circuit `workflow_guidance` or Sentieon module answers.

- [ ] **Step 2: Make source inclusion match the same boundaries**

Update `sources.py` so:
- external error-association files are only considered when the query is obviously external and error-like
- they do not become generic evidence for Sentieon workflow or module prompts
- normal external guides still appear for explanatory format/tool questions

- [ ] **Step 3: Only touch `reference_intents.py` if the new tests prove a heuristic gap**

If needed, keep the change minimal:
- preserve `workflow_guidance`
- preserve existing script/module/parameter intent precedence
- only add heuristics required for clearly external error phrasing

- [ ] **Step 4: Run the routing and CLI regression tests**

Run:

```bash
pytest -q tests/test_sources.py
pytest -q tests/test_cli.py -k "external or reference"
pytest -q tests/test_reference_intents.py
```

Expected:
- source inclusion/exclusion stays deterministic
- CLI output still uses compact stable sections
- no new regression in workflow guidance or module routing

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/answering.py src/sentieon_assist/sources.py src/sentieon_assist/reference_intents.py tests/test_sources.py tests/test_cli.py tests/test_reference_intents.py
git commit -m "feat: keep error association routing deterministic"
```

## Chunk 4: Final Verification and Operator-Facing Sync

### Task 7: Update repo-level docs and verify the full suite

**Files:**
- Modify: `README.md`
- Modify: `docs/project-context.md`
- Modify: `sentieon-note/README.md`

- [ ] **Step 1: Update user-facing docs with the completed association surface**

Document:
- which high-frequency external error families are now covered deterministically
- what the assistant will and will not claim
- that Sentieon workflow selection still comes only from official Sentieon material

- [ ] **Step 2: Run the baseline suite used in this repo**

Run:

```bash
pytest -q tests/test_answering.py tests/test_classifier.py tests/test_sources.py tests/test_reference_intents.py tests/test_cli.py tests/test_llm_backends.py
```

Expected:
- all tests pass

- [ ] **Step 3: Run one manual chat smoke after the suite is green**

Run:

```bash
cd /Users/zhuge/Documents/codex/harness
PYTHONPATH=src python3.11 -m sentieon_assist chat
```

Try:
- `VCF 报 contig not found 是什么情况`
- `BED 区间总是差一位是为什么`
- `BAM 报 read group 不一致怎么办`
- `如果我要做wgs分析，能不能给个指导`

Expected:
- external error queries return `【关联判断】` and `【优先检查】`
- explanatory external queries still return `【资料说明】`
- workflow questions still return `【流程指导】`

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project-context.md sentieon-note/README.md
git commit -m "docs: finalize high-frequency error association coverage"
```

### Task 8: Final handoff checklist

**Files:**
- No code changes required unless verification uncovers a regression

- [ ] **Step 1: Capture the final covered matrix in the PR or handoff note**

List the final deterministic families:
- bgzip/tabix and VCF indexing
- Read Group / header mismatch
- CRAM / reference mismatch
- contig naming / dictionary mismatch
- BED coordinate-system mismatch
- FASTA / FAI / dict companion mismatch
- BAM sorting / indexing state

- [ ] **Step 2: Record any remaining explicit gaps**

If a family is still not backed by local official material, state it directly as:
- `本地官方资料未覆盖`
- `待核验占位`

Do not silently infer missing remediation steps.

- [ ] **Step 3: Stop**

At this point the high-frequency association layer is complete enough for deterministic execution without mixing external rules into Sentieon primary workflow guidance.
