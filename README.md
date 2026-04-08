# Sentieon Assist MVP v0

Offline CLI harness for a local Sentieon technical-support assistant.

## Why this is a harness

This project does not send every question straight to the model. It uses a
controlled flow:

1. classify the issue
2. extract minimum structured information
3. stop and ask for missing required information when needed
4. try external rule packs first
5. prefer deterministic local-source answers for module and parameter queries
6. use the local Ollama model as the primary generation backend only when needed
7. optionally allow a separately configured fallback LLM backend later

That is the main engineering difference between a harness and a raw prompt.

## Runtime requirements

- Python 3.11+
- local Ollama HTTP API
- a local model such as `gemma4:e4b`

## Configuration

- `OLLAMA_BASE_URL`
  - default: `http://127.0.0.1:11434`
- `OLLAMA_MODEL`
  - default: `gemma4:e4b`
- `OLLAMA_KEEP_ALIVE`
  - default: `30m`
  - example: `2h` or `-1`
- `SENGENT_LLM_FALLBACK_BACKEND`
  - optional
  - supported values today: `ollama`, `openai_compatible`
- `SENGENT_LLM_FALLBACK_BASE_URL`
  - optional base URL for the fallback backend
- `SENGENT_LLM_FALLBACK_MODEL`
  - optional fallback model name
- `SENGENT_LLM_FALLBACK_API_KEY`
  - optional API key for `openai_compatible` fallback backends
- `SENTIEON_ASSIST_KNOWLEDGE_DIR`
  - optional override directory for customer-site knowledge packs
- `SENTIEON_ASSIST_SOURCE_DIR`
  - optional override directory for local manuals, release notes, and notes

## Knowledge packs

Bundled starter packs live in:

- `knowledge/base/license.json`
- `knowledge/base/install.json`

Customer deployments should override or extend these through
`SENTIEON_ASSIST_KNOWLEDGE_DIR` instead of editing Python code.

Reference materials for source-backed answers can be mounted through
`SENTIEON_ASSIST_SOURCE_DIR`.

The curated Sentieon module index now lives in the mounted source bundle:

- `sentieon-note/sentieon-modules.json`
- `sentieon-note/sentieon-module-index.md`

## Example usage

```bash
PYTHONPATH=src python3 -m sentieon_assist.cli "Sentieon 202503 license 报错，找不到 license 文件"
```

```bash
OLLAMA_MODEL=gemma4:e4b PYTHONPATH=src python3 -m sentieon_assist.cli "Sentieon 202503 install 失败，解压后命令不可用"
```

For customer-site testing without changing shell environment:

```bash
PYTHONPATH=src python3 -m sentieon_assist.cli \
  --knowledge-dir /path/to/customer-knowledge \
  --source-dir /path/to/customer-sources \
  "Sentieon 202503 install 失败，解压后命令不可用"
```

## Interactive terminal mode

```bash
PYTHONPATH=src python3 -m sentieon_assist chat
```

Then enter questions one by one. Use `/quit` to exit.

Current chat behavior:

- all turns show a single-line `思考中...` animation before output starts
- model-backed turns stream progressively when Ollama returns chunks
- chat startup warms up the local model to reduce first-turn latency
- rule-first answers remain the backbone; the local model mainly handles natural follow-up wording and answer polishing

## Environment doctor

Use the built-in doctor command before customer-site troubleshooting:

```bash
PYTHONPATH=src python3 -m sentieon_assist doctor
```

It reports:

- local Ollama API reachability
- configured model name and whether it is available
- recent model load and eval durations when available
- effective knowledge directory and file count
- effective source directory and file count
- primary source-bundle release/date inferred from the mounted materials when available

## Source inspection

List local reference materials:

```bash
PYTHONPATH=src python3 -m sentieon_assist --source-dir /path/to/customer-sources sources
```

The source list shows a trust tier:

- `official`: primary source, such as the local Sentieon release PDF
- `derived`: internal summaries, maps, and curated notes
- `secondary`: helpful but lower-priority references such as the Chinese overview

Search local reference materials by keyword:

```bash
PYTHONPATH=src python3 -m sentieon_assist --source-dir /path/to/customer-sources search SENTIEON_LICENSE
```

When a final answer is backed by mounted materials, the CLI now appends a
`【资料版本】` section so the operator can see which primary Sentieon release the
current answer is anchored to.

If the user's requested Sentieon version clearly differs from the mounted
primary release, the CLI also adds a `【版本提示】` section before execution advice.

For reference-style module/parameter answers, the user-visible chat/CLI output
is now intentionally slimmer: internal trace sections such as `【资料查询】`,
`【资料版本】`, and `【参考资料】` are hidden from the final displayed answer.

For reference-style searches, the search path now ranks curated module/index
materials ahead of long generic PDF mentions, so queries such as `DNAscope`
prefer the structured local index when both sources mention the same term.

## Natural Knowledge Queries

The same `cli` and `chat` entry points can answer local reference questions about
Sentieon modules and common parameters, for example:

```bash
PYTHONPATH=src python3 -m sentieon_assist.cli "DNAscope 是做什么的"
```

```bash
PYTHONPATH=src python3 -m sentieon_assist.cli "sentieon-cli dnascope 的 --pcr_free 是什么"
```

The assistant answers these by preferring mounted local notes and source
snippets. For module-intro questions and the currently indexed high-frequency
parameter questions, it now prefers the curated module index first and answers
them deterministically before involving the model. Uncovered parameter/detail
questions still fall back to local source evidence.

For compact customer-facing output:

- module intro questions still show `【模块介绍】`
- parameter questions now prefer a shorter `【常用参数】` answer
- ambiguous parameter names first ask the user to confirm the module, then
  continue on the next turn

## Recommended Local Testing

```bash
export PYTHONPATH=src
export OLLAMA_KEEP_ALIVE=30m
python3 -m sentieon_assist doctor
python3 -m sentieon_assist chat
```
