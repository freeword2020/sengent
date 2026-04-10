# 2026-04-10 Sengent Release Packaging Follow-up

## Goal

Close the last ordinary-user delivery gaps after the external install review:

1. make runtime guidance distinguish connectivity failure vs missing model
2. make CLI help and misplaced-global-option errors actionable
3. make installer output teach users to activate the venv and use the installed `sengent` command
4. document how users obtain the package before installation
5. add a repeatable release packaging script for GitHub Releases

## Scope

- `src/sentieon_assist/runtime_guidance.py`
- `src/sentieon_assist/cli.py`
- `scripts/install_sengent.sh`
- `scripts/package_release.sh`
- `README.md`
- `README.zh-CN.md`
- `docs/sengent-user-guide.md`
- `docs/sengent-maintainer-guide.md`
- targeted tests for runtime guidance, CLI, installer, docs, and packaging

## Verification

- targeted release-UX pytest subset
- full `python3.11 -m pytest -q`
- `python3.11 scripts/pilot_readiness_eval.py`
- `python3.11 scripts/pilot_closed_loop.py`
- real `scripts/package_release.sh` run
- real build-only installer run
- real runtime-host installer run
