# Sengent Final Delivery Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten Sengent into a release-quality delivery that installs cleanly on macOS/Linux, defaults to the installed `sengent` command, keeps the renew pipeline portable and rollback-safe, and ships coherent user/operator documentation.

**Architecture:** Preserve the current rule-first, structured-pack-first runtime and renew pipeline. Final delivery work focuses on packaging stability, portable default paths, operator safety, documentation coherence, and adversarial pre-push review rather than changing the support-routing philosophy.

**Tech Stack:** Python 3.11, setuptools, Bash installer, local Ollama HTTP API, optional `docling`, `pytest`, structured JSON packs, runtime/build artifacts under app-home-managed directories.

---

### Task 1: Release-hardening for install and paths

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/pyproject.toml`
- Modify: `/Users/zhuge/Documents/codex/harness/scripts/install_sengent.sh`
- Create: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/app_paths.py`
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/config.py`
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/session_events.py`
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/knowledge_build.py`
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/doctor.py`
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/cli.py`
- Test: `/Users/zhuge/Documents/codex/harness/tests/test_app_paths.py`
- Test: `/Users/zhuge/Documents/codex/harness/tests/test_install_script.py`
- Test: `/Users/zhuge/Documents/codex/harness/tests/test_packaging_contract.py`
- Test: `/Users/zhuge/Documents/codex/harness/tests/test_doctor.py`

- [x] Add installed `sengent` entrypoint
- [x] Move default runtime/build/inbox/source paths to app-home-managed directories
- [x] Install non-editably instead of `-e`
- [x] Seed active source packs during install
- [x] Make `doctor --skip-ollama` real

### Task 2: Delivery doc coherence

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/README.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/local-ollama-environment.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/sengent-user-guide.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/sengent-maintainer-guide.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/superpowers/operators/2026-04-10-sengent-team-briefing.md`
- Modify: `/Users/zhuge/Documents/codex/harness/knowledge/README.md`

- [x] Default docs to installed `sengent` usage
- [x] Separate user runtime flow from maintainer/release verification flow
- [x] Document app-home paths, activation manifests, and backup recovery
- [x] Remove misleading direct-pack-edit guidance

### Task 3: Final review and release verification

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/docs/superpowers/specs/2026-04-09-sengent-knowledge-build-system-design.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/superpowers/architecture/2026-04-10-sengent-knowledge-build-architecture.md`
- Verify only

- [x] Run adversarial architecture/documentation review
- [x] Fix blocking packaging/operator findings
- [ ] Run full verification
- [ ] Commit and push final delivery
