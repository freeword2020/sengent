# Sengent 2.0 Milestone 2 Knowledge Taxonomy Upgrade Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `Sengent 2.0` from the Phase 1 five-pack compatibility bridge to a real six-pack knowledge taxonomy with a runtime pack registry, including a first-class `incident-memory` pack and logical-pack-based access paths.

**Architecture:** Keep the current physical filenames for the five existing `Sentieon` packs to avoid unnecessary churn, but add a sixth runtime pack `incident-memory.json` and introduce a kernel-level pack registry that resolves logical pack kinds through vendor profiles. Runtime loaders and source/evidence utilities must stop treating filenames as the knowledge model and instead consume logical pack kinds through the registry.

**Tech Stack:** Python 3.11, pytest, existing Sengent CLI/build pipeline, vendor profiles, kernel pack contracts

---

## Scope Boundary

This plan implements **Milestone 2 only** from the approved 2.0 spec: the knowledge taxonomy upgrade.

This plan explicitly includes:

- six-pack taxonomy support
- runtime pack registry / logical-pack resolution
- regression coverage for the existing vendor profile contract fields already introduced in Milestone 1
- build / doctor / activate / rollback support for the six-pack contract
- pack-health validation for missing and malformed required packs
- migration of runtime knowledge loaders away from scattered filename ownership

This plan explicitly does **not** implement Milestone 3 or Milestone 4 work:

- support-intent upgrades
- clarify/fallback runtime policy
- canonical boundary output shapes
- answer contracts
- controlled learning loop
- gap-record capture
- unsupported-version runtime decision handling

Those remain separate execution units after Milestone 2 lands.

## Chunk 1: Add A Runtime Pack Registry And Six-Pack Contract

### Task 1: Introduce a kernel pack registry with failing tests first

**Files:**
- Create: `src/sentieon_assist/kernel/pack_runtime.py`
- Modify: `src/sentieon_assist/kernel/__init__.py`
- Modify: `src/sentieon_assist/vendors/sentieon/profile.py`
- Create: `tests/test_pack_runtime.py`
- Modify: `tests/test_vendor_profiles.py`

- [ ] **Step 1: Write the failing registry tests**

Add tests that assert:

- logical pack resolution works through the vendor profile, not hard-coded filenames
- `Sentieon` exposes all six logical packs, including `incident-memory`
- `incident-memory` resolves to a runtime JSON pack file
- required-pack completeness can be checked against an on-disk source directory using logical kinds
- malformed required packs are reported as invalid / runtime-incomplete instead of silently loading
- the Sentieon profile keeps `incident-memory` explicitly `required=True`
- the existing vendor profile contract fields remain intact:
  - `vendor_id`
  - `display_name`
  - `default_version`
  - `supported_versions`
  - `pack_manifest`
  - `domain_dependencies`
  - `clarification_policy`
  - `support_boundaries`
- each manifest entry still exposes:
  - `required`
  - `file_name`
  - `entry_schema_version`
  - `load_order`

Example shape:

```python
def test_pack_runtime_resolves_sentieon_incident_memory_pack():
    resolved = resolve_pack_file("sentieon", "incident-memory")
    assert resolved.file_name == "incident-memory.json"
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_pack_runtime.py tests/test_vendor_profiles.py -k "incident or runtime"`
Expected: FAIL because the runtime pack registry and `incident-memory.json` mapping do not exist yet.

- [ ] **Step 3: Implement the kernel pack runtime module**

In `src/sentieon_assist/kernel/pack_runtime.py`, define:

- a resolved-pack dataclass or equivalent typed structure
- `resolve_pack_entry(vendor_id, logical_kind)`
- `pack_path_for_kind(source_directory, vendor_id, logical_kind)`
- `required_pack_status(source_directory, vendor_id)`
- a focused validation helper for required runtime pack files
- any focused helper needed to list required pack files in manifest order

Keep this module vendor-agnostic. It should delegate all pack ownership to vendor profiles.

- [ ] **Step 4: Promote `incident-memory` to a runtime JSON pack in the Sentieon profile**

Update `src/sentieon_assist/vendors/sentieon/profile.py` so:

- `incident-memory` points to `incident-memory.json`
- `incident-memory` remains explicitly `required=True` for the Sentieon profile
- the five existing physical filenames remain unchanged
- the profile still expresses the six-pack 2.0 contract

- [ ] **Step 5: Run targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_pack_runtime.py tests/test_vendor_profiles.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/sentieon_assist/kernel/__init__.py src/sentieon_assist/kernel/pack_runtime.py src/sentieon_assist/vendors/sentieon/profile.py tests/test_pack_runtime.py tests/test_vendor_profiles.py
git commit -m "feat: add runtime pack registry for taxonomy upgrade"
```

## Chunk 2: Upgrade Build, Doctor, Activate, And Rollback To The Six-Pack Taxonomy

### Task 2: Make the managed runtime pack set explicitly six packs

**Files:**
- Modify: `src/sentieon_assist/knowledge_build.py`
- Modify: `src/sentieon_assist/doctor.py`
- Modify: `src/sentieon_assist/cli.py`
- Modify: `tests/test_knowledge_build.py`
- Modify: `tests/test_doctor.py`
- Modify: `tests/test_cli.py`
- Create: `sentieon-note/incident-memory.json`

- [ ] **Step 1: Write the failing build/doctor tests**

Add tests that prove:

- managed-pack completeness now includes `incident-memory.json`
- `doctor` reports a missing `incident-memory.json` when absent
- `doctor` reports malformed required runtime packs as invalid / incomplete
- build/activate/rollback preserve six physical runtime pack files
- the repository’s baseline Sentieon note directory contains a valid empty `incident-memory.json`

Example shape:

```python
def test_missing_managed_pack_files_includes_incident_memory(tmp_path):
    ...
    assert "incident-memory.json" in missing
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_doctor.py tests/test_cli.py -k "incident_memory or managed_pack"`
Expected: FAIL because the current managed set still excludes `incident-memory`.

- [ ] **Step 3: Update build/doctor/CLI to use the six-pack managed set**

Refactor the Phase 1 compatibility boundary in `knowledge_build.py` and `doctor.py` so:

- `ACTIVE_MANAGED_LOGICAL_KINDS` becomes the full six-pack runtime set
- completeness checks, activation, rollback, and candidate-pack generation all include `incident-memory`
- malformed required runtime packs are surfaced as invalid instead of being treated as healthy
- CLI/operator messages stay explicit about runtime-required packs

Add `sentieon-note/incident-memory.json` as an empty valid pack:

```json
{
  "version": "",
  "entries": []
}
```

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_doctor.py tests/test_cli.py -k "incident_memory or managed_pack"`
Expected: PASS

- [ ] **Step 5: Run broader regression buckets**

Run:

- `python3.11 -m pytest -q tests/test_pack_runtime.py tests/test_pack_contract.py tests/test_vendor_profiles.py`
- `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_doctor.py tests/test_cli.py`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/sentieon_assist/knowledge_build.py src/sentieon_assist/doctor.py src/sentieon_assist/cli.py tests/test_knowledge_build.py tests/test_doctor.py tests/test_cli.py sentieon-note/incident-memory.json
git commit -m "feat: add six-pack runtime taxonomy support"
```

## Chunk 3: Move Runtime Knowledge Access To Logical Pack Kinds

### Task 3: Replace direct filename ownership in runtime loaders and source utilities

**Files:**
- Modify: `src/sentieon_assist/module_index.py`
- Modify: `src/sentieon_assist/workflow_index.py`
- Modify: `src/sentieon_assist/external_guides.py`
- Modify: `src/sentieon_assist/sources.py`
- Create: `src/sentieon_assist/incident_memory.py`
- Modify: `tests/test_sources.py`
- Modify: `tests/test_workflow_index.py`
- Create: `tests/test_incident_memory.py`

- [ ] **Step 1: Write the failing runtime-loader tests**

Add tests that prove:

- module/workflow/external-guide loaders resolve their source file through logical pack kinds
- `sources.py` assigns trust/priority using the pack registry rather than hard-coded filenames
- `incident_memory.py` can load the new pack when present
- missing or malformed `incident-memory` remains a runtime-health failure surfaced through the pack registry / doctor path, not a silent empty normalization

Example shape:

```python
def test_module_index_uses_vendor_reference_pack_resolution(tmp_path, monkeypatch):
    ...
    assert list_module_entries(tmp_path)
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_sources.py tests/test_workflow_index.py tests/test_incident_memory.py -k "pack or incident"`
Expected: FAIL because the loaders and source ranking still own filenames directly.

- [ ] **Step 3: Refactor the runtime loaders**

Update:

- `module_index.py` to resolve `vendor-reference`
- `workflow_index.py` to resolve `vendor-decision`
- `external_guides.py` to resolve `domain-standard`, `playbook`, and `troubleshooting`
- `sources.py` to derive pack trust/priority from the pack registry while preserving current non-pack document ordering
- add `incident_memory.py` as the first loader for `incident-memory`

Do not change user-facing runtime behavior beyond the taxonomy ownership shift.

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `python3.11 -m pytest -q tests/test_sources.py tests/test_workflow_index.py tests/test_incident_memory.py`
Expected: PASS

- [ ] **Step 5: Run compatibility regressions for answering/reference flows**

Run:

- `python3.11 -m pytest -q tests/test_answering.py tests/test_reference_resolution.py tests/test_support_coordinator.py`
- `python3.11 -m pytest -q tests/test_sources.py tests/test_workflow_index.py tests/test_incident_memory.py`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/sentieon_assist/module_index.py src/sentieon_assist/workflow_index.py src/sentieon_assist/external_guides.py src/sentieon_assist/sources.py src/sentieon_assist/incident_memory.py tests/test_sources.py tests/test_workflow_index.py tests/test_incident_memory.py
git commit -m "refactor: route runtime knowledge loaders through pack registry"
```

## Final Verification

- [ ] **Step 1: Run the full Milestone 2 suite**

Run:

```bash
python3.11 -m pytest -q \
  tests/test_pack_contract.py \
  tests/test_pack_runtime.py \
  tests/test_vendor_profiles.py \
  tests/test_knowledge_build.py \
  tests/test_doctor.py \
  tests/test_cli.py \
  tests/test_sources.py \
  tests/test_workflow_index.py \
  tests/test_incident_memory.py \
  tests/test_answering.py \
  tests/test_reference_resolution.py \
  tests/test_support_coordinator.py
```

Expected: PASS

- [ ] **Step 2: Review the taxonomy-upgrade surface**

Run:

```bash
sed -n '1,220p' docs/superpowers/specs/2026-04-12-sengent-2-0-support-kernel-design.md
sed -n '1,260p' docs/superpowers/plans/2026-04-13-sengent-2-0-milestone-2-taxonomy-upgrade.md
sed -n '1,220p' src/sentieon_assist/kernel/pack_runtime.py
sed -n '1,200p' src/sentieon_assist/vendors/sentieon/profile.py
sed -n '1,220p' src/sentieon_assist/incident_memory.py
rg -n 'sentieon-modules\\.json|workflow-guides\\.json|external-format-guides\\.json|external-tool-guides\\.json|external-error-associations\\.json' src/sentieon_assist/module_index.py src/sentieon_assist/workflow_index.py src/sentieon_assist/external_guides.py src/sentieon_assist/sources.py
```

Expected:

- runtime pack ownership is expressed through the pack registry / vendor profile path
- `incident-memory.json` exists as a first-class runtime pack
- malformed or missing required packs are visible through the runtime pack health path
- the old five filenames may still appear in tests and profile declarations, but not as scattered ownership logic across runtime modules

- [ ] **Step 3: Commit any final cleanup**

```bash
git add docs/superpowers/plans/2026-04-13-sengent-2-0-milestone-2-taxonomy-upgrade.md
git commit -m "docs: capture sengent 2.0 milestone 2 plan"
```
