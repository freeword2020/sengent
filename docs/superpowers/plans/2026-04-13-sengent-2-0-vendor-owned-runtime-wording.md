# Vendor-Owned Runtime Wording Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move vendor-owned runtime wording assets out of kernel-facing Sentieon hard-codes and into a minimal vendor profile contract while preserving the current Sentieon-first answer semantics and clarify behavior.

**Architecture:** Keep answer-contract headers, section ordering, semantic field ids, and control flow in the kernel. Extend `VendorProfile` with a minimal runtime wording asset for field labels, capability bullets, and official material terms, then let `support_coordinator.py`, `answering.py`, and `answer_contracts.py` render their existing contracts from that asset.

**Tech Stack:** Python 3.11, pytest, existing vendor profile registry, current runtime answer/clarify modules

---

## Scope Boundary

This plan covers only the second low-risk decoupling chunk for runtime wording ownership.

It explicitly includes:

- vendor-owned field labels
- requirement alias derivation
- capability explanation wording assets
- unsupported-version official material wording assets
- compatibility-focused tests

It explicitly excludes:

- second vendor implementation
- query lexicon generalization
- compile heuristics
- physical pack changes
- activate / rollback
- runtime truth-path behavior

## File Map

- Modify: `src/sentieon_assist/vendors/base.py`
  - add minimal runtime wording dataclass / contract
- Modify: `src/sentieon_assist/vendors/sentieon/profile.py`
  - provide Sentieon runtime wording assets with current semantics
- Modify: `src/sentieon_assist/support_coordinator.py`
  - resolve clarification slot labels from profile wording
- Modify: `src/sentieon_assist/answering.py`
  - resolve missing-field labels and capability wording from profile wording
- Modify: `src/sentieon_assist/answer_contracts.py`
  - resolve official-material wording from profile wording while keeping section headers in kernel
- Modify: `tests/test_vendor_profiles.py`
  - contract tests for runtime wording assets
- Modify: `tests/test_support_coordinator.py`
  - slot inference tests continue to pass through profile labels
- Modify: `tests/test_answering.py`
  - wording remains Sentieon-first but profile-driven

## Chunk 1: Lock The Runtime Wording Contract In Tests

### Task 1: Add failing tests for vendor-owned wording assets

**Files:**
- Modify: `tests/test_vendor_profiles.py`
- Modify: `tests/test_support_coordinator.py`
- Modify: `tests/test_answering.py`

- [ ] **Step 1: Add vendor profile wording tests**

Cover:

- profile exposes runtime wording asset
- runtime wording asset has:
  - `field_labels`
  - `capability_summary_lines`
  - `capability_example_queries`
  - `official_material_terms`
- Sentieon wording keeps the current `Sentieon 版本` label

- [ ] **Step 2: Add support coordinator / answering tests**

Cover:

- open clarification slot inference still works through profile-provided labels
- `answer_query()` still starts with `需要补充以下信息：Sentieon 版本`
- capability explanation still describes current Sentieon support scope
- unsupported-version boundary and gap-record material requests still ask for the same class of official materials

- [ ] **Step 3: Run focused tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_vendor_profiles.py tests/test_support_coordinator.py tests/test_answering.py -k "runtime_wording or capability or unsupported_version or clarification"
```

Expected: FAIL because runtime wording assets are not yet defined on the vendor profile.

## Chunk 2: Add The Minimal Vendor Runtime Wording Contract

### Task 2: Extend the vendor profile surface without creating a full UI text system

**Files:**
- Modify: `src/sentieon_assist/vendors/base.py`
- Modify: `src/sentieon_assist/vendors/sentieon/profile.py`
- Modify: `tests/test_vendor_profiles.py`

- [ ] **Step 1: Implement the minimal wording dataclass**

Add a small contract such as:

- `field_labels`
- `capability_summary_lines`
- `capability_example_queries`
- `official_material_terms`

Avoid:

- generic arbitrary text registries
- section headers
- whole-answer templates

- [ ] **Step 2: Populate Sentieon wording assets**

Preserve the current semantics and wording shape for Sentieon.

- [ ] **Step 3: Run focused tests to verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_vendor_profiles.py -k "runtime_wording"
```

Expected: PASS

## Chunk 3: Rewire Runtime Field Labels And Clarify Text

### Task 3: Move field labels and requirement alias ownership into the profile

**Files:**
- Modify: `src/sentieon_assist/support_coordinator.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `tests/test_support_coordinator.py`
- Modify: `tests/test_answering.py`

- [ ] **Step 1: Replace hard-coded field label maps**

Route:

- `FIELD_SLOT_LABELS`
- `FIELD_LABELS`
- `REQUIREMENT_FIELD_ALIASES`

through vendor wording assets or thin helper functions.

- [ ] **Step 2: Keep semantic field ids stable**

Do not change:

- `version`
- `error`
- `input_type`
- `data_type`
- `step`

- [ ] **Step 3: Run focused tests to verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_support_coordinator.py tests/test_answering.py -k "clarification or missing_fields or resolved_default_vendor"
```

Expected: PASS

## Chunk 4: Rewire Capability And Official Material Wording

### Task 4: Move the highest-value vendor-facing text while keeping kernel structure

**Files:**
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/answer_contracts.py`
- Modify: `tests/test_answering.py`

- [ ] **Step 1: Migrate capability explanation wording**

Move vendor-facing bullets and example prompts into the profile wording asset, but keep:

- `【能力说明】`
- `【建议下一步】`

as kernel-owned section headers.

- [ ] **Step 2: Migrate official material request wording**

Move the vendor-facing part of:

- unsupported-version gap-record `missing_materials`
- unsupported-version / no-answer official material references

into the wording asset.

- [ ] **Step 3: Keep boundary phrasing stable**

Do not rewrite generic kernel boundary lines such as:

- “不能直接给出确定性建议”
- “先补齐下面列出的材料”

- [ ] **Step 4: Run focused tests to verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_answering.py -k "capability or unsupported_version or no_answer_boundary"
```

Expected: PASS

## Chunk 5: Compatibility Regression

### Task 5: Prove Sentieon-first wording behavior still holds

**Files:**
- Verify only

- [ ] **Step 1: Run the wording-facing suite**

Run:

```bash
python3.11 -m pytest -q tests/test_vendor_profiles.py tests/test_support_coordinator.py tests/test_answering.py
```

Expected: PASS

- [ ] **Step 2: Review boundary-sensitive output**

Confirm that:

- Sentieon wording still appears where expected
- capability explanation meaning is unchanged
- clarification slot inference still works
- answer contract section headers remain kernel-owned

- [ ] **Step 3: Commit**

```bash
git add src/sentieon_assist/vendors/base.py src/sentieon_assist/vendors/sentieon/profile.py src/sentieon_assist/support_coordinator.py src/sentieon_assist/answering.py src/sentieon_assist/answer_contracts.py tests/test_vendor_profiles.py tests/test_support_coordinator.py tests/test_answering.py
git commit -m "refactor: move runtime wording into vendor profile"
```

## Explicit Non-Goals For Execution

Do not include the following in the first wording chunk:

- query lexicon rewrites
- compile heuristic changes
- source pack changes
- operator or CLI wording sweeps
- broad answer phrasing rewrites outside the selected wording assets
