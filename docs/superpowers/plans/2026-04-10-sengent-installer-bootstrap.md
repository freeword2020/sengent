# Sengent Installer Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cross-platform install/bootstrap script that lets Linux/macOS users set up Sengent from a git checkout with one command, including Python dependencies and Ollama preflight.

**Architecture:** Keep the installer thin and operator-facing. The shell script should orchestrate environment creation, package installation, and doctor/preflight reporting, while the application remains the source of truth for runtime health. Ollama must stay an optional installation-time assist, not a shell-CLI runtime dependency.

**Tech Stack:** Bash, Python 3.11+, non-editable `pip` install, installed `sengent` CLI, optional `docling`, optional Ollama CLI/model pull.

---

## Chunk 1: Installer Contract Tests

### Task 1: Lock installer CLI behavior with dry-run tests

**Files:**
- Create: `/Users/zhuge/Documents/codex/harness/tests/test_install_script.py`
- Test: `/Users/zhuge/Documents/codex/harness/scripts/install_sengent.sh`

- [ ] **Step 1: Write failing tests**

Add tests that require:
- `scripts/install_sengent.sh --help` to print usage and key flags
- `--dry-run --skip-ollama` to print venv creation, non-editable install, source-pack seeding, and installed doctor steps
- `--dry-run --with-pdf-build` to print the optional `.[pdf-build]` install path
- `--dry-run --ensure-ollama-model` without an `ollama` binary on `PATH` to warn instead of failing

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3.11 -m pytest -q tests/test_install_script.py`
Expected: FAIL because the script does not exist yet.

## Chunk 2: Installer Script

### Task 2: Implement a portable bootstrap script

**Files:**
- Create: `/Users/zhuge/Documents/codex/harness/scripts/install_sengent.sh`

- [ ] **Step 1: Add a minimal Bash installer**

Implement:
- `--help`
- `--python <path>`
- `--venv-dir <path>`
- `--with-pdf-build`
- `--skip-ollama`
- `--ensure-ollama-model`
- `--ollama-base-url <url>`
- `--ollama-model <model>`
- `--dry-run`

Behavior:
- resolve repo root from script path
- create venv without sourcing it
- install package non-editably
- optionally install `.[pdf-build]` or maintainer extras
- seed active source packs into the app-home-managed source directory
- run installed `sengent doctor`
- optionally attempt `ollama pull <model>` only if `--ensure-ollama-model` is passed and the CLI exists
- otherwise print clear next steps

- [ ] **Step 2: Re-run installer tests**

Run: `python3.11 -m pytest -q tests/test_install_script.py`
Expected: PASS

## Chunk 3: Docs

### Task 3: Document the one-command install path

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/README.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/local-ollama-environment.md`

- [ ] **Step 1: Add install instructions**

Document:
- standard install command
- PDF-capable install option
- Ollama preflight expectation
- optional model pull behavior

- [ ] **Step 2: Keep runtime rule intact**

Explicitly note:
- Ollama HTTP API is still the runtime integration path
- shell `ollama` CLI is only an installation-time convenience when available

## Chunk 4: Verification

### Task 4: Verify installer and core stability

**Files:**
- Verify only

- [ ] **Step 1: Run installer-focused tests**

Run: `python3.11 -m pytest -q tests/test_install_script.py tests/test_packaging_contract.py tests/test_doctor.py`
Expected: PASS

- [ ] **Step 2: Run full test suite**

Run: `python3.11 -m pytest -q`
Expected: PASS
