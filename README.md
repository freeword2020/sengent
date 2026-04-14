# Sengent

Governance-first CLI support system for Sentieon software support.

Chinese README: [README.zh-CN.md](README.zh-CN.md)

![Sengent Home](docs/assets/sengent-home.svg)

## What Changed In 2.1

Sengent 1.0 used Ollama as the primary runtime path.

Sengent 2.1 keeps the same support-kernel and knowledge-governance model, but the primary runtime path now uses an **OpenAI-compatible API**.

That change does **not** relax the core boundaries:

- runtime truth still comes from reviewed active knowledge packs
- raw docs still do not become runtime truth
- factory hosted drafting is still offline and review-only
- clarify-first, boundary pack, tool arbitration, and rollback stay in place

## Package Download

Preferred download path:

1. Open [GitHub Releases](https://github.com/freeword2020/sengent/releases)
2. Download `sengent-<version>.tar.gz` or `sengent-<version>.zip`
3. Extract it
4. `cd` into the extracted `sengent-<version>/` directory

Fallback if you do not have a release bundle yet:

1. Open the repository page
2. Click the green `Code` button
3. Choose `Download ZIP`
4. Extract it and enter the extracted repo directory

If you are preparing GitHub release assets from a checkout:

```bash
bash scripts/package_release.sh --output-dir dist
```

This produces both `dist/sengent-<version>.tar.gz` and `dist/sengent-<version>.zip`.

## Quick Start

### Runtime Host Using An OpenAI-Compatible API

```bash
tar -xzf sengent-<version>.tar.gz
cd sengent-<version>
bash scripts/install_sengent.sh
source .venv/bin/activate

export SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible
export SENGENT_RUNTIME_LLM_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_RUNTIME_LLM_MODEL=your-runtime-model
export SENGENT_RUNTIME_LLM_API_KEY=your-runtime-api-key

export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key

sengent doctor
sengent chat
```

If you only want hosted runtime and not hosted factory yet, configure the four `SENGENT_RUNTIME_LLM_*` variables first and add the factory variables later.

### Build / Review Host

```bash
tar -xzf sengent-<version>.tar.gz
cd sengent-<version>
bash scripts/install_sengent.sh --with-maintainer-tools --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

### Legacy Ollama Path

If you still want the old local-model path, 2.1 can still run it explicitly:

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
OLLAMA_BASE_URL=http://127.0.0.1:11434 OLLAMA_MODEL=gemma4:e4b sengent doctor
```

Treat this as a compatibility path, not the primary 2.1 install story.

## Requirements

### Primary 2.1 runtime

- Python `3.11+`
- an OpenAI-compatible API endpoint
- a valid runtime model id and API key

### Optional hosted factory drafting

- another OpenAI-compatible endpoint or the same one
- a valid factory model id and API key

### Optional legacy runtime

- local Ollama HTTP API
- a locally available model such as `gemma4:e4b`

### Core dependencies

- `rich`
- `PyYAML`

### Optional maintainer extras

- `pytest`
- `docling`

## Install Script Notes

`scripts/install_sengent.sh` now:

- creates a local virtualenv
- installs Sengent non-editably from the current checkout
- seeds the active source pack directory from the managed JSON packs, including `incident-memory.json`
- runs the installed `sengent doctor`
- keeps the old `--ensure-ollama-model` path only for legacy Ollama setup

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

## Runtime And Factory API Configuration

### Required runtime variables

```bash
export SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible
export SENGENT_RUNTIME_LLM_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_RUNTIME_LLM_MODEL=your-runtime-model
export SENGENT_RUNTIME_LLM_API_KEY=your-runtime-api-key
```

### Optional hosted factory variables

```bash
export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key
```

### Optional runtime capability overrides

```bash
export SENGENT_RUNTIME_LLM_SUPPORTS_TOOLS=true
export SENGENT_RUNTIME_LLM_SUPPORTS_JSON_SCHEMA=true
export SENGENT_RUNTIME_LLM_SUPPORTS_REASONING_EFFORT=false
export SENGENT_RUNTIME_LLM_SUPPORTS_STREAMING=true
export SENGENT_RUNTIME_LLM_MAX_CONTEXT=128000
export SENGENT_RUNTIME_LLM_PROMPT_CACHE_BEHAVIOR=provider-default
```

### Legacy compatibility variables

```bash
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=gemma4:e4b
export OLLAMA_KEEP_ALIVE=30m
```

## Installed Command

After installation, the default command is:

```bash
sengent
```

Typical usage:

```bash
sengent --help
sengent doctor
sengent chat
sengent "What does DNAscope do?"
sengent sources
sengent search SENTIEON_LICENSE
```

## Docs

- Chinese README: [README.zh-CN.md](README.zh-CN.md)
- User guide, English: [docs/sengent-user-guide.en.md](docs/sengent-user-guide.en.md)
- User guide, Chinese: [docs/sengent-user-guide.md](docs/sengent-user-guide.md)
- Maintainer guide, English: [docs/sengent-maintainer-guide.en.md](docs/sengent-maintainer-guide.en.md)
- Maintainer guide, Chinese: [docs/sengent-maintainer-guide.md](docs/sengent-maintainer-guide.md)
- 2.1 GitHub release package, English: [docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.md](docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.md)
- 2.1 GitHub release package, Chinese: [docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.zh-CN.md](docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.zh-CN.md)
- Legacy Ollama environment notes: [docs/local-ollama-environment.md](docs/local-ollama-environment.md)
