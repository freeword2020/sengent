# Sengent

Offline CLI harness for a local Sentieon technical-support assistant.

Chinese README: [README.zh-CN.md](README.zh-CN.md)

![Sengent Home](docs/assets/sengent-home.svg)

## What Sengent Is

Sengent is a local Sentieon support system for:

- onboarding and workflow guidance
- troubleshooting
- module / parameter / script lookup
- controlled knowledge updates with build / gate / activate / rollback

It is deliberately **not** a RAG-first chat bot and **not** a model-first router.

## Design Intent

Sengent is built around five engineering rules:

- rule-first routing
- structured packs as runtime truth
- raw docs only for build, audit, and traceability
- eval-gated activation before knowledge goes live
- backup and rollback before and after every apply

The local model is part of the runtime, but only as a **controlled generator**.
It does not decide top-level routing, and it does not define runtime truth.

## Runtime Architecture

There are two major paths:

1. **Runtime support path**
   - `support_coordinator`
   - deterministic reference / workflow / module access
   - controlled answer generation
   - session / event / feedback trace
2. **Knowledge renew path**
   - raw docs / sidecar metadata
   - `knowledge build`
   - candidate packs
   - gate
   - `knowledge activate`
   - automatic backups
   - `knowledge rollback`

## Compatibility

- macOS: supported
- Linux: supported
- Windows: not a primary target in this delivery

## Quick Start For Ordinary Users

If you want a runtime host that can answer questions right away:

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
sengent doctor
sengent chat
```

If this machine is only for knowledge build / review work:

```bash
bash scripts/install_sengent.sh --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

If you do not know which command to run next, start with:

```bash
sengent --help
```

## Requirements

### Runtime

- Python `3.11+`
- local Ollama HTTP API for chat / query runtime
- a local model such as `gemma4:e4b`

### Core dependencies

- `rich`
- `PyYAML`

### Optional dependencies

- `docling`
  - only needed for PDF-backed knowledge build

### Maintainer tools

- `pytest`
- `docling`

The installer can provision the right dependency set for normal users or maintainers.

## Install

### Runtime host install

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
sengent doctor
sengent chat
```

Use this on hosts that should answer questions.

### Build-only host install

```bash
bash scripts/install_sengent.sh --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

Use this on hosts that only handle build / review / gate / activate.

### Maintainer install

```bash
bash scripts/install_sengent.sh --with-maintainer-tools
source .venv/bin/activate
sengent doctor --skip-ollama
```

### What the installer does

`scripts/install_sengent.sh` now:

- creates a local virtualenv
- installs Sengent **non-editably** from the current checkout
- seeds the active source pack directory from the repo’s managed JSON packs
- runs the installed `sengent doctor`
- optionally pulls the configured Ollama model when the `ollama` CLI is available

Useful flags:

```bash
bash scripts/install_sengent.sh --python /path/to/python3.11
bash scripts/install_sengent.sh --venv-dir /custom/.venv
bash scripts/install_sengent.sh --with-pdf-build
bash scripts/install_sengent.sh --with-maintainer-tools
bash scripts/install_sengent.sh --refresh-active-sources
bash scripts/install_sengent.sh --skip-ollama
bash scripts/install_sengent.sh --ensure-ollama-model
bash scripts/install_sengent.sh --dry-run
```

If your host uses an internal Python package mirror, set it before running the installer:

```bash
export PIP_INDEX_URL=https://your-internal-pypi/simple
bash scripts/install_sengent.sh --with-maintainer-tools
```

## Installed Command

After install, the default command is:

```bash
sengent
```

Typical usage:

```bash
sengent --help
sengent doctor
sengent chat
sengent "DNAscope 是做什么的"
sengent sources
sengent search SENTIEON_LICENSE
```

## If Runtime Chat Is Not Ready Yet

If Sengent says the model or local runtime is unavailable:

1. Run `sengent doctor`
2. Confirm whether this host is a runtime host or only a build-only host
3. If it is a runtime host, make sure the Ollama HTTP API is reachable
4. If the service is up but the model is missing, run:

```bash
ollama pull gemma4:e4b
```

If this host is only for build / review work, use:

```bash
sengent doctor --skip-ollama
```

## Default Paths

By default Sengent now uses a user-owned app home instead of the repo checkout.

### macOS

- app home: `~/Library/Application Support/Sengent`

### Linux

- app home: `$XDG_DATA_HOME/sengent`
- fallback: `~/.local/share/sengent`

### Important subdirectories

- active source packs: `<app-home>/sources/active`
- knowledge inbox: `<app-home>/knowledge-inbox/sentieon`
- runtime logs: `<app-home>/runtime`
- knowledge builds: `<app-home>/runtime/knowledge-build`

You can override these with environment variables when needed:

- `SENGENT_HOME`
- `SENTIEON_ASSIST_SOURCE_DIR`
- `SENTIEON_ASSIST_KNOWLEDGE_DIR`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_KEEP_ALIVE`

Optional fallback backend settings:

- `SENGENT_LLM_FALLBACK_BACKEND`
- `SENGENT_LLM_FALLBACK_BASE_URL`
- `SENGENT_LLM_FALLBACK_MODEL`
- `SENGENT_LLM_FALLBACK_API_KEY`

## Common User Commands

```bash
sengent --help
sengent doctor
sengent chat
sengent "sentieon-cli dnascope 的 --pcr_free 是什么"
sengent "能给个 rnaseq 的参考脚本吗"
sengent sources
sengent search DNAscope
```

## Common Maintainer Commands

```bash
sengent knowledge scaffold --kind module --id fastdedup --name FastDedup
sengent knowledge build
sengent knowledge review
sengent knowledge activate --build-id <build_id>
sengent knowledge rollback --backup-id <backup_id>
```

For a customer-site bundle override:

```bash
sengent --source-dir /path/to/customer-sources doctor --skip-ollama
sengent --source-dir /path/to/customer-sources knowledge build
```

## Testing And Gates

Two different levels matter:

- **runtime / maintainer operations**
  - use `sengent doctor`
  - use `sengent knowledge build/review/activate/rollback`
- **developer / release verification**
  - run `python -m pytest -q`
  - run the pilot gate scripts from the repo checkout

See the maintainer guide for the exact gate commands and required `--json-out` artifacts.

## Documentation

- Chinese README: [README.zh-CN.md](README.zh-CN.md)
- User guide: [docs/sengent-user-guide.md](docs/sengent-user-guide.md)
- Maintainer guide: [docs/sengent-maintainer-guide.md](docs/sengent-maintainer-guide.md)
- Ollama runtime guide: [docs/local-ollama-environment.md](docs/local-ollama-environment.md)
- Operator manual: [docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md](docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md)
- Team briefing: [docs/superpowers/operators/2026-04-10-sengent-team-briefing.md](docs/superpowers/operators/2026-04-10-sengent-team-briefing.md)
- Architecture: [docs/superpowers/architecture/2026-04-10-sengent-knowledge-build-architecture.md](docs/superpowers/architecture/2026-04-10-sengent-knowledge-build-architecture.md)
