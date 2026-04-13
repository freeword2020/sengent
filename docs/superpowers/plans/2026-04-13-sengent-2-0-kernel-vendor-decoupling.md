# Kernel-Vendor Decoupling Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize default vendor resolution and thread vendor-aware pack access through kernel-facing helpers so Sengent remains Sentieon-first in behavior while reducing structural coupling to hard-coded Sentieon assumptions.

**Architecture:** Leave vendor-owned content and compile heuristics in place for now, but replace scattered `"sentieon"` caller fallbacks with a single vendor-resolution contract. Then let pack accessor wrappers and managed-pack helpers consume that contract without changing physical pack names, runtime truth rules, or activation semantics.

**Tech Stack:** Python 3.11, pytest, existing vendor profile registry, kernel pack runtime helpers, current Sengent CLI/build/runtime modules

---

## Scope Boundary

This plan covers only the first low-risk decoupling chunk.

It explicitly includes:

- centralized default vendor resolution
- vendor-aware pack access wrapper defaults
- runtime/build/doctor caller contract cleanup
- compatibility-focused tests

It explicitly excludes:

- second vendor implementation
- vendor-content wording migration
- compile heuristic generalization
- source layout changes
- active pack or truth-path behavior changes

## File Map

- Modify: `src/sentieon_assist/vendors/__init__.py`
  - central default vendor helpers
  - canonical vendor id normalization
- Modify: `src/sentieon_assist/support_coordinator.py`
  - route decision vendor defaulting through the resolver
- Modify: `src/sentieon_assist/answering.py`
  - answer path vendor fallback through the resolver
- Modify: `src/sentieon_assist/module_index.py`
  - optional `vendor_id` on pack access helpers
- Modify: `src/sentieon_assist/external_guides.py`
  - optional `vendor_id` on pack access helpers
- Modify: `src/sentieon_assist/incident_memory.py`
  - optional `vendor_id` on pack access helpers
- Modify: `src/sentieon_assist/knowledge_build.py`
  - centralize default vendor in inbox / managed-pack helper layer only
- Modify: `src/sentieon_assist/doctor.py`
  - centralize default vendor in managed-pack health helper layer only
- Modify: `tests/test_vendor_profiles.py`
  - vendor resolver contract tests
- Modify: `tests/test_pack_runtime.py`
  - pack path contract tests remain stable with explicit vendor ids
- Modify: `tests/test_knowledge_build.py`
  - build helper defaulting behavior tests
- Modify: `tests/test_doctor.py`
  - doctor helper defaulting behavior tests

## Chunk 1: Lock The Default Vendor Resolution Contract

### Task 1: Add failing tests for the new defaulting rules

**Files:**
- Modify: `tests/test_vendor_profiles.py`
- Modify: `tests/test_knowledge_build.py`
- Modify: `tests/test_doctor.py`

- [ ] **Step 1: Add vendor registry defaulting tests**

Cover:

- a canonical default vendor helper returns `sentieon`
- explicit `sentieon` resolves identically
- unknown vendor ids still raise clearly

Example shape:

```python
def test_resolve_vendor_id_defaults_to_sentieon():
    assert resolve_vendor_id(None) == "sentieon"
```

- [ ] **Step 2: Add build/doctor caller defaulting tests**

Cover:

- build/doctor helper paths use the resolver instead of private `"sentieon"` literals
- monkeypatching the resolver affects the helper layer where intended
- current default behavior remains unchanged

- [ ] **Step 3: Run focused tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_vendor_profiles.py tests/test_knowledge_build.py tests/test_doctor.py -k "resolve_vendor or default_vendor or managed_pack"
```

Expected: FAIL because a centralized default vendor contract does not exist yet.

## Chunk 2: Implement Vendor Resolution And Thread It Through Callers

### Task 2: Replace scattered caller fallbacks with the central contract

**Files:**
- Modify: `src/sentieon_assist/vendors/__init__.py`
- Modify: `src/sentieon_assist/support_coordinator.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `src/sentieon_assist/doctor.py`

- [ ] **Step 1: Implement the central resolver**

Add:

- `DEFAULT_VENDOR_ID`
- `resolve_vendor_id(...)`
- optional `default_vendor_profile()`

Requirements:

- normalize case/whitespace
- default to `sentieon`
- reject unknown vendor ids clearly

- [ ] **Step 2: Route runtime callers through the resolver**

Update:

- `support_coordinator.py`
- `answering.py`

Requirements:

- no direct `"sentieon"` fallback in caller logic
- keep current effective runtime behavior
- do not change answer wording in this task

- [ ] **Step 3: Route build/doctor helper defaults through the resolver**

Update only the helper/default layer in:

- `knowledge_build.py`
- `doctor.py`

Do not change:

- compile heuristics
- pack file names
- activation behavior

- [ ] **Step 4: Run focused tests to verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_vendor_profiles.py tests/test_knowledge_build.py tests/test_doctor.py -k "resolve_vendor or default_vendor or managed_pack"
```

Expected: PASS

## Chunk 3: Add Vendor-Aware Pack Access Wrapper Parameters

### Task 3: Decouple pack accessor wrappers from hard-coded Sentieon constants

**Files:**
- Modify: `src/sentieon_assist/module_index.py`
- Modify: `src/sentieon_assist/external_guides.py`
- Modify: `src/sentieon_assist/incident_memory.py`
- Modify: `tests/test_pack_runtime.py`

- [ ] **Step 1: Add failing wrapper tests**

Cover:

- pack accessor wrappers accept explicit `vendor_id`
- default behavior still resolves to the current Sentieon packs
- wrappers rely on the central resolver / pack runtime path rather than local constants

- [ ] **Step 2: Run focused tests to verify they fail**

Run:

```bash
python3.11 -m pytest -q tests/test_pack_runtime.py -k "pack_path or explicit_vendor or module_index"
```

Expected: FAIL because wrapper modules still use local Sentieon constants.

- [ ] **Step 3: Implement optional `vendor_id` on wrappers**

Update pack path / file-name helpers in:

- `module_index.py`
- `external_guides.py`
- `incident_memory.py`

Requirements:

- no behavior change when omitted
- no content/heuristic rewrite

- [ ] **Step 4: Run focused tests to verify pass**

Run:

```bash
python3.11 -m pytest -q tests/test_pack_runtime.py -k "pack_path or explicit_vendor or module_index"
```

Expected: PASS

## Chunk 4: Compatibility Regression

### Task 4: Prove Sentieon-first behavior remains intact

**Files:**
- Verify only

- [ ] **Step 1: Run the contract and integration suite**

Run:

```bash
python3.11 -m pytest -q tests/test_vendor_profiles.py tests/test_pack_runtime.py tests/test_knowledge_build.py tests/test_doctor.py
```

Expected: PASS

- [ ] **Step 2: Run adjacent runtime regression buckets**

Run:

```bash
python3.11 -m pytest -q tests/test_support_coordinator.py tests/test_answering.py
```

Expected: PASS

- [ ] **Step 3: Review boundary-sensitive code paths**

Check that no changes touched:

- compile candidate entry semantics
- reference wording / capability wording
- activation / rollback
- runtime truth path

- [ ] **Step 4: Commit**

```bash
git add src/sentieon_assist/vendors/__init__.py src/sentieon_assist/support_coordinator.py src/sentieon_assist/answering.py src/sentieon_assist/module_index.py src/sentieon_assist/external_guides.py src/sentieon_assist/incident_memory.py src/sentieon_assist/knowledge_build.py src/sentieon_assist/doctor.py tests/test_vendor_profiles.py tests/test_pack_runtime.py tests/test_knowledge_build.py tests/test_doctor.py
git commit -m "refactor: centralize vendor defaults in kernel callers"
```

## Explicit Non-Goals For Execution

Do not include the following in this plan’s first implementation chunk:

- rewriting Sentieon-facing answer text
- generalizing query lexicons
- changing physical pack names
- changing scaffold kind taxonomy
- removing Sentieon-specific compile heuristics
- introducing a second vendor profile implementation
