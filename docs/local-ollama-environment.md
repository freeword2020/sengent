# Local Ollama Environment

Date checked: 2026-04-07

## Current status

- Installed desktop app: `Ollama 0.20.0`
- App path: `/Applications/Ollama.app`
- Local model manifest present:
  - `~/.ollama/models/manifests/registry.ollama.ai/library/gemma4/e4b`
- Local HTTP API is the supported integration path for this project

## Confirmed working path

The desktop app is currently exposing a local HTTP server on:

- `http://127.0.0.1:11434`

Confirmed endpoints:

- `GET /api/version` -> `200`
- `GET /api/tags` -> includes `gemma4:e4b`
- `POST /api/generate` with `gemma4:e4b` -> successful response

This means the project can rely on the local Ollama HTTP API without depending
on the GUI itself.

## Known issues

- The shell `ollama` CLI currently crashes during local execution in this
  environment.
- Sandbox-local loopback access may fail even when the host machine can reach
  `127.0.0.1:11434`.
- Historical Ollama log files contain older Gemma 4 loading failures. They do
  not reflect the current desktop app runtime because the HTTP API now succeeds.

## Project rule

This harness project must integrate with Ollama through the local HTTP API:

- do use: configurable `OLLAMA_BASE_URL` and `OLLAMA_MODEL`
- do not rely on: desktop GUI actions
- do not require: shell `ollama` CLI for runtime behavior

## Portability implications

For customer-site installation:

- Ollama host must be configurable
- model id must be configurable
- Sentieon knowledge files must be external to code
- future model swaps should require configuration changes, not code edits
