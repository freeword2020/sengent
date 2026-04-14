# Sengent 2.1 GitHub Release Package

## Release Summary

- Sengent 1.0 used Ollama as the primary runtime path.
- Sengent 2.1 uses an OpenAI-compatible API as the primary runtime path.
- The support kernel stays governance-first.
- Runtime truth still comes from reviewed active knowledge packs.
- Hosted factory drafting stays offline and review-only.

## Release Assets

Upload these GitHub release assets:

- `sengent-<version>.tar.gz`
- `sengent-<version>.zip`

Generate them from repo root with:

```bash
bash scripts/package_release.sh --output-dir dist
```

## Installation Notes

### Runtime host

```bash
bash scripts/install_sengent.sh
source .venv/bin/activate

export SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible
export SENGENT_RUNTIME_LLM_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_RUNTIME_LLM_MODEL=your-runtime-model
export SENGENT_RUNTIME_LLM_API_KEY=your-runtime-api-key

sengent doctor
sengent chat
```

### Optional hosted factory drafting

```bash
export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key
```

### Build / review host

```bash
bash scripts/install_sengent.sh --with-maintainer-tools --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

## User Notes

- 2.1 is not a raw-doc RAG bot
- clarify-first remains the default when evidence is insufficient
- if runtime health is bad, start from `sengent doctor`
- factory hosted drafting does not change runtime truth automatically

## Maintainer Notes

- do not bypass build / review / gate / activate
- do not let hosted drafts write into active packs directly
- preserve rollback and auditability
- use real customer failures to backfill the adversarial corpus

## Legacy Compatibility Note

Legacy Ollama runtime remains available for explicit compatibility use:

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
```

That path remains supported as a compatibility mode, not as the primary 2.1 release story.
