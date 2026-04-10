# Sengent Release UX Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten Sengent's release UX so installed users can discover commands, diagnose runtime prerequisites, and follow bilingual installation guidance without reading the codebase.

**Architecture:** Keep the existing rule-first runtime and renew pipeline intact. Focus this batch on the delivery surface: the installed CLI must expose help and actionable runtime guidance; doctor output must explain what to do when Ollama is missing; and the repository entry docs must separate runtime users from build-only maintainers in both English and Chinese.

**Tech Stack:** Python 3.11+, existing CLI/doctor/install shell, pytest, Markdown docs.

---

### Task 1: Lock the release UX contracts with failing tests

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_cli.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_doctor.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_install_script.py`

- [ ] **Step 1: Add failing CLI help tests**
- [ ] **Step 2: Run targeted CLI tests and confirm they fail for current help behavior**
- [ ] **Step 3: Add failing runtime guidance tests for chat/query error handling**
- [ ] **Step 4: Add failing doctor formatting tests for actionable Ollama guidance**
- [ ] **Step 5: Run targeted doctor/runtime tests and confirm they fail**

### Task 2: Implement CLI help and runtime-friendly error surfacing

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/cli.py`
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/ollama_client.py`

- [ ] **Step 1: Add top-level and command-specific help text for installed `sengent`**
- [ ] **Step 2: Make `sengent`, `sengent --help`, and `sengent help` show usage instead of falling into query mode**
- [ ] **Step 3: Add friendly Ollama/runtime guidance formatter for chat and single-query failures**
- [ ] **Step 4: Keep low-level error text available inside the guidance output for debugging**
- [ ] **Step 5: Re-run the targeted CLI tests until green**

### Task 3: Improve doctor output and install-path guidance

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/src/sentieon_assist/doctor.py`
- Modify: `/Users/zhuge/Documents/codex/harness/scripts/install_sengent.sh`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_doctor.py`
- Modify: `/Users/zhuge/Documents/codex/harness/tests/test_install_script.py`

- [ ] **Step 1: Extend doctor output with actionable next-step guidance for skipped/error/model-missing states**
- [ ] **Step 2: Tighten installer help/output so runtime-host vs build-host behavior is obvious**
- [ ] **Step 3: Re-run targeted doctor/installer tests until green**

### Task 4: Rewrite the delivery docs for technical and nontechnical users

**Files:**
- Modify: `/Users/zhuge/Documents/codex/harness/README.md`
- Create: `/Users/zhuge/Documents/codex/harness/README.zh-CN.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/sengent-user-guide.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/sengent-maintainer-guide.md`
- Modify: `/Users/zhuge/Documents/codex/harness/docs/local-ollama-environment.md`

- [ ] **Step 1: Rewrite the English README around installed `sengent` usage and nontechnical quick start**
- [ ] **Step 2: Add a Chinese README with mirrored installation and usage guidance**
- [ ] **Step 3: Tighten user and maintainer guides so build-only hosts and runtime hosts are clearly separated**
- [ ] **Step 4: Recheck command examples to ensure they all use installed `sengent`**

### Task 5: Verify the merged release branch and publish

**Files:**
- Verify only

- [ ] **Step 1: Run targeted UX-focused pytest suites**
- [ ] **Step 2: Run the full pytest suite**
- [ ] **Step 3: Run `python3.11 scripts/pilot_readiness_eval.py`**
- [ ] **Step 4: Run `python3.11 scripts/pilot_closed_loop.py`**
- [ ] **Step 5: Review git diff, commit the UX hardening batch, and push `main`**
