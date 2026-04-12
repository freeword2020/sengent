# Sengent 2.0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the first reusable `Sengent 2.0` support-kernel foundation by formalizing platform principles, adding a vendor profile contract, and centralizing pack contracts so the codebase is no longer structurally locked to a single hard-coded Sentieon-only shape.

**Architecture:** Keep the proven `1.x` build/gate/activate backbone, but introduce an explicit `vendor profile + pack contract` layer in front of it. Phase 1 intentionally stops at foundation work: docs, interfaces, registry/loading, and contract-driven wiring in `knowledge_build`/`doctor`, while preserving current runtime behavior.

**Tech Stack:** Python 3.11, pytest, setuptools package layout, existing Sengent CLI/build pipeline

---

## Chunk 1: Lock The 2.0 Contracts In Docs And Tests

### Task 1: Add failing docs-contract tests for the 2.0 platform guidance

**Files:**
- Modify: `tests/test_docs_contract.py`
- Create: `docs/superpowers/architecture/2026-04-12-sengent-2-0-platform-principles.md`
- Create: `docs/superpowers/operators/2026-04-12-sengent-vendor-onboarding-contract.md`

- [ ] **Step 1: Write the failing docs tests**

Add tests that assert the new docs exist and cover:

- support kernel vs vendor profile separation
- evidence hierarchy
- clarify-first rule when evidence is insufficient
- answer contract as a first-class kernel rule
- controlled learning loop / gap capture as a first-class kernel rule
- vendor onboarding requirements:
  - official sources
  - domain standards
  - playbooks
  - incident cases
  - eval corpus
  - support boundaries

Example shape:

```python
def test_platform_principles_doc_exists_with_kernel_rules():
    text = (REPO_ROOT / "docs/superpowers/architecture/2026-04-12-sengent-2-0-platform-principles.md").read_text(encoding="utf-8")
    assert "support kernel" in text
    assert "vendor profile" in text
    assert "证据不足时先澄清" in text
    assert "answer contract" in text
    assert "controlled learning loop" in text
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_docs_contract.py -k "platform_principles or vendor_onboarding"`
Expected: FAIL because the new docs and assertions do not exist yet.

- [ ] **Step 3: Write the platform guidance docs**

Create:

- `docs/superpowers/architecture/2026-04-12-sengent-2-0-platform-principles.md`
- `docs/superpowers/operators/2026-04-12-sengent-vendor-onboarding-contract.md`

The docs must be short, direct, and implementation-oriented. They should not restate the whole spec; they should define the durable rules future software profiles must follow.

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_docs_contract.py -k "platform_principles or vendor_onboarding"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_docs_contract.py docs/superpowers/architecture/2026-04-12-sengent-2-0-platform-principles.md docs/superpowers/operators/2026-04-12-sengent-vendor-onboarding-contract.md
git commit -m "docs: add sengent 2.0 platform contracts"
```

## Chunk 2: Introduce Vendor Profile And Pack Contract Primitives

### Task 2: Add failing tests for vendor profiles and pack contracts

**Files:**
- Create: `src/sentieon_assist/kernel/__init__.py`
- Create: `src/sentieon_assist/kernel/pack_contract.py`
- Create: `src/sentieon_assist/vendors/__init__.py`
- Create: `src/sentieon_assist/vendors/base.py`
- Create: `src/sentieon_assist/vendors/sentieon/__init__.py`
- Create: `src/sentieon_assist/vendors/sentieon/profile.py`
- Create: `tests/test_pack_contract.py`
- Create: `tests/test_vendor_profiles.py`

- [ ] **Step 1: Write the failing contract tests**

Add tests for:

- logical 2.0 pack kinds:
  - `vendor-reference`
  - `vendor-decision`
  - `domain-standard`
  - `playbook`
  - `troubleshooting`
  - `incident-memory`
- required fields on a vendor profile:
  - `vendor_id`
  - `display_name`
  - `default_version`
  - `supported_versions`
  - `pack_manifest`
  - `domain_dependencies`
  - `clarification_policy`
  - `support_boundaries`
- registry lookup for `sentieon`
- manifest entry schema fields for each required logical pack:
  - `required`
  - `file_name`
  - `entry_schema_version`
  - `load_order`
- completeness helper failure behavior when any of the six required logical pack kinds is missing

Example shape:

```python
def test_sentieon_profile_exposes_minimum_vendor_contract():
    profile = get_vendor_profile("sentieon")
    assert profile.vendor_id == "sentieon"
    assert "vendor-reference" in profile.pack_manifest
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_pack_contract.py tests/test_vendor_profiles.py`
Expected: FAIL because the new modules and registry do not exist.

- [ ] **Step 3: Implement the kernel pack contract module**

In `src/sentieon_assist/kernel/pack_contract.py`, define:

- canonical 2.0 logical pack kinds
- a `PackManifestEntry` dataclass
- helpers for required-pack completeness checks

Keep this module software-agnostic. Do not hard-code `Sentieon` names here.

- [ ] **Step 4: Implement vendor profile base and Sentieon profile**

Create:

- `src/sentieon_assist/vendors/base.py`
- `src/sentieon_assist/vendors/sentieon/profile.py`
- `src/sentieon_assist/vendors/__init__.py`

The Sentieon profile should:

- satisfy the base contract
- declare current physical pack filenames through its manifest
- preserve current `1.x` runtime file names for now
- clearly separate logical pack kinds from physical file names

- [ ] **Step 5: Run targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_pack_contract.py tests/test_vendor_profiles.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/sentieon_assist/kernel/__init__.py src/sentieon_assist/kernel/pack_contract.py src/sentieon_assist/vendors/__init__.py src/sentieon_assist/vendors/base.py src/sentieon_assist/vendors/sentieon/__init__.py src/sentieon_assist/vendors/sentieon/profile.py tests/test_pack_contract.py tests/test_vendor_profiles.py
git commit -m "feat: add sengent 2.0 vendor profile contracts"
```

## Chunk 3: Rewire Build And Doctor To Use The New Contracts

### Task 3: Add failing tests for vendor-aware pack completeness checks

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `src/sentieon_assist/doctor.py`
- Modify: `tests/test_knowledge_build.py`
- Modify: `tests/test_doctor.py`

- [ ] **Step 1: Write the failing integration tests**

Add tests proving that:

- managed-pack completeness is derived from the Sentieon profile manifest, not a free-floating hard-coded filename tuple
- doctor reports missing managed packs through the profile contract
- knowledge build still preserves current physical file behavior
- activate still preserves current physical file behavior
- rollback still preserves current physical file behavior

Example shape:

```python
def test_missing_managed_pack_files_uses_vendor_profile_manifest(tmp_path):
    ...
    assert "external-tool-guides.json" in missing
```

The point is not to change filenames yet; the point is to centralize ownership of those filenames.

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_doctor.py -k "managed_pack or vendor_profile or missing_managed_pack"`
Expected: FAIL because `knowledge_build.py` and `doctor.py` still use direct hard-coded file lists.

- [ ] **Step 3: Route managed-pack logic through the Sentieon profile**

Refactor `src/sentieon_assist/knowledge_build.py` so:

- `PACK_ENTRY_TYPES`, `MANAGED_PACK_FILES`, and scaffold routing no longer act as the sole source of truth
- the Sentieon vendor profile supplies the active manifest mapping
- legacy physical filenames remain unchanged in this milestone

Do not introduce the full 2.0 six-pack physical migration yet. This task is about ownership and interfaces.

- [ ] **Step 4: Update doctor to use the same contract**

Refactor `src/sentieon_assist/doctor.py` so managed-pack completeness and missing-pack reporting use the vendor profile / pack contract instead of a separate implicit list.

- [ ] **Step 5: Run targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_doctor.py -k "managed_pack or vendor_profile or missing_managed_pack"`
Expected: PASS

- [ ] **Step 6: Run compatibility regression buckets**

Run:

- `python3.11 -m pytest -q tests/test_pack_contract.py tests/test_vendor_profiles.py`
- `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_doctor.py tests/test_support_coordinator.py tests/test_reference_resolution.py`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/sentieon_assist/knowledge_build.py src/sentieon_assist/doctor.py tests/test_knowledge_build.py tests/test_doctor.py src/sentieon_assist/pack_contract.py src/sentieon_assist/vendors
git commit -m "refactor: drive managed packs through vendor contracts"
```

## Final Verification

- [ ] **Step 1: Run the full targeted foundation suite**

Run:

```bash
python3.11 -m pytest -q \
  tests/test_docs_contract.py \
  tests/test_pack_contract.py \
  tests/test_vendor_profiles.py \
  tests/test_knowledge_build.py \
  tests/test_doctor.py \
  tests/test_support_coordinator.py \
  tests/test_reference_resolution.py
```

Expected: PASS

- [ ] **Step 2: Review the new 2.0 foundation artifacts**

Run:

```bash
sed -n '1,240p' docs/superpowers/specs/2026-04-12-sengent-2-0-support-kernel-design.md
sed -n '1,220p' docs/superpowers/architecture/2026-04-12-sengent-2-0-platform-principles.md
sed -n '1,220p' docs/superpowers/operators/2026-04-12-sengent-vendor-onboarding-contract.md
sed -n '1,220p' src/sentieon_assist/kernel/pack_contract.py
sed -n '1,220p' src/sentieon_assist/vendors/sentieon/profile.py
rg -n "MANAGED_PACK_FILES|PACK_ENTRY_TYPES|SCAFFOLD_KIND_TO_PACK_TARGET" src/sentieon_assist/knowledge_build.py src/sentieon_assist/doctor.py
```

Expected:

- The repository now has a clear kernel/profile split on paper and in code
- `knowledge_build.py` and `doctor.py` now read managed-pack ownership from the profile/contract path rather than each owning an implicit file list
- The current Sentieon runtime remains behaviorally compatible

- [ ] **Step 3: Commit any final cleanup**

```bash
git add docs/superpowers/specs/2026-04-12-sengent-2-0-support-kernel-design.md docs/superpowers/plans/2026-04-12-sengent-2-0-foundation.md
git commit -m "docs: capture sengent 2.0 foundation plan"
```
