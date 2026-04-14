# Sengent User Guide

## Audience

This guide is for everyday users who ask Sengent for Sentieon support, troubleshooting, and parameter or script lookup.

## What 2.1 Means For Users

- Sengent 1.0 primarily used Ollama for local runtime
- Sengent 2.1 primarily uses an OpenAI-compatible API
- runtime truth still comes from reviewed active knowledge packs
- hosted factory drafting stays offline and review-only

## Prerequisites

### Runtime host

- Python `3.11+`
- an OpenAI-compatible API endpoint
- a runtime model id
- a runtime API key

### Optional hosted factory drafting

- factory provider / base URL / model / API key

### Compatibility path

If you still need the old local-model route, you can explicitly keep using Ollama, but that is no longer the primary 2.1 setup.

## Installation

### 1. Get the package

Prefer downloading `sengent-<version>.tar.gz` or `.zip` from [GitHub Releases](https://github.com/freeword2020/sengent/releases).

If a release bundle is not available yet, use `Download ZIP` from the repository page.

### 2. Install the CLI

```bash
tar -xzf sengent-<version>.tar.gz
cd sengent-<version>
bash scripts/install_sengent.sh
source .venv/bin/activate
```

### 3. Configure the runtime API

```bash
export SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible
export SENGENT_RUNTIME_LLM_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_RUNTIME_LLM_MODEL=your-runtime-model
export SENGENT_RUNTIME_LLM_API_KEY=your-runtime-api-key
```

If you also want hosted factory drafting:

```bash
export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key
```

### 4. Run the first health check

```bash
sengent doctor
```

Check these first:

- runtime provider is `openai_compatible`
- runtime `model_available` is `yes`
- `managed_pack_complete` is `yes`
- if factory hosted is configured, `review_only` remains `yes`

### 5. Start asking questions

```bash
sengent chat
```

Or ask a single-shot question:

```bash
sengent "What does DNAscope do?"
sengent "Can GVCFtyper run on a limited interval?"
```

## Common Commands

```bash
sengent --help
sengent doctor
sengent chat
sengent sources
sengent search SENTIEON_LICENSE
```

## Support Boundaries

- Sengent is not a raw-doc RAG bot
- factory drafts do not become runtime truth automatically
- when evidence is insufficient, the correct behavior is to clarify first
- true file-format or structural consistency issues may be routed through tool arbitration first

## If The Answer Is Not Good Enough

Use `/feedback` in chat and keep:

1. the original question
2. the original answer
3. the answer or next step you expected

## When To Escalate To A Maintainer

Escalate quickly when:

- `managed_pack_complete: no`
- provider / model / API key look correct but `doctor` still fails
- knowledge needs to be added, revised, or removed
- a real customer case should be backfilled into the eval corpus
