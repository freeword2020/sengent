# Sengent Maintainer Guide

## Audience

This guide is for maintainers who manage knowledge updates, prepare release bundles, run build / review / gate / activate / rollback, and backfill real support failures into the corpus.

## What Changed In 2.1

- Sengent 1.0 was Ollama-first
- Sengent 2.1 is OpenAI-compatible-API-first
- knowledge governance remains unchanged
- runtime truth still comes only from reviewed active packs
- hosted factory drafting still stays review-only

## Two Host Types

### 1. Build / Review host

This host is for:

- source intake
- build
- review
- gate
- activate / rollback

Recommended install:

```bash
tar -xzf sengent-<version>.tar.gz
cd sengent-<version>
bash scripts/install_sengent.sh --with-maintainer-tools --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

### 2. Combined runtime + maintainer host

If the same machine also serves real support runtime, configure the OpenAI-compatible API runtime first:

```bash
tar -xzf sengent-<version>.tar.gz
cd sengent-<version>
bash scripts/install_sengent.sh --with-maintainer-tools
source .venv/bin/activate

export SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible
export SENGENT_RUNTIME_LLM_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_RUNTIME_LLM_MODEL=your-runtime-model
export SENGENT_RUNTIME_LLM_API_KEY=your-runtime-api-key

sengent doctor
```

If hosted factory drafting is enabled, also configure:

```bash
export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key
```

## Release Bundles

From repo root:

```bash
bash scripts/package_release.sh --output-dir dist
```

Default artifacts:

- `dist/sengent-<version>.tar.gz`
- `dist/sengent-<version>.zip`

Upload both to GitHub Releases.

## Installer Behavior

`scripts/install_sengent.sh`:

- creates a virtualenv
- installs Sengent non-editably
- seeds the managed JSON packs into the active source dir
- runs `sengent doctor`
- keeps `--ensure-ollama-model` only as a legacy Ollama compatibility path

## Boundaries Maintainers Must Preserve

- do not turn the system into raw-doc runtime retrieval
- do not let the hosted model become runtime truth
- do not let hosted factory drafts bypass review into active packs
- every knowledge change must go through build / review / gate / activate
- rollback first when the knowledge state is suspect

## Maintainer Workflow

### 1. Intake / Scaffold

```bash
sengent knowledge scaffold --kind module --id fastdedup --name FastDedup
```

### 2. Build

```bash
sengent knowledge build
```

### 3. Review

```bash
sengent knowledge review
```

### 4. Gate

```bash
python scripts/pilot_readiness_eval.py
python scripts/pilot_closed_loop.py
```

### 5. Activate

```bash
sengent knowledge activate --build-id <build_id>
```

### 6. Rollback

```bash
sengent knowledge rollback --backup-id <backup_id>
```

## Recommended Verification

```bash
pytest -q tests/test_install_script.py tests/test_docs_contract.py
python3.11 scripts/adversarial_support_drill.py
pytest -q
```

## Related Docs

- [README.md](../README.md)
- [README.zh-CN.md](../README.zh-CN.md)
- [docs/sengent-user-guide.en.md](./sengent-user-guide.en.md)
- [docs/sengent-user-guide.md](./sengent-user-guide.md)
- [2026-04-14-sengent-2-1-github-release-package.md](./superpowers/operators/2026-04-14-sengent-2-1-github-release-package.md)
