# Sentieon Assist Project Context

This document is the handoff anchor for future threads working on
`sentieon-assist`. It captures why the project exists, what is already built,
what architectural boundaries matter, and which milestones have been completed.

## Project Goal

Build a practical local Sentieon support assistant for Chinese-speaking
operators and customers. The assistant is designed for environments where:

- questions are asked in Chinese or mixed Chinese/English
- local reference materials are available on disk
- a local Ollama model such as `gemma4:e4b` is deployed on-site
- the system must be explainable and safer than a raw prompt-only chatbot

The long-term target is a reliable, deployable support assistant that can keep
growing through future threads without losing architecture or product context.

## Current Product Shape

The current product is an offline CLI harness with:

- rule-first troubleshooting for `license` and `install`
- structured extraction of key fields such as version and input type
- Chinese-first and mixed-language query handling
- local-reference-backed answers with release/version context
- interactive chat mode backed by local Ollama
- a non-fullscreen `Sengent` chat shell rendered with `rich`
- a startup welcome panel plus per-turn event stream in chat
- streaming output in chat with a visible `思考中...` status line
- natural local reference queries for Sentieon modules and common parameters

Primary runtime entry points:

- `python3.11 -m sentieon_assist.cli "question"`
- `python3.11 -m sentieon_assist chat`
- `python3.11 -m sentieon_assist doctor`
- `python3.11 -m sentieon_assist sources`
- `python3.11 -m sentieon_assist search KEYWORD`

## Important Architectural Rules

These constraints matter and should be preserved unless intentionally replaced:

1. Rule-first remains the core pattern.
   The assistant should not send every question straight to the model.

2. Local references are first-class evidence.
   Answers should prefer `sentieon-note/` and mounted local source bundles.

3. The local model is an assistant layer, not the source of truth.
   It can reorganize, polish, and phrase answers naturally, but should not
   bypass the rule/database/reference backbone.

4. Chinese customer UX is a primary requirement.
   Query classification, field extraction, and follow-up questions should not
   assume English-only phrasing.

5. Deployment assumes local Ollama exists.
   Chat mode currently requires a local model and does not intentionally
   degrade into a model-free conversational path.

## Current Code Map

Key files and responsibilities:

- `src/sentieon_assist/cli.py`
  CLI entrypoint, chat loop, thinking animation, model warmup, streaming output,
  and natural query routing.

- `src/sentieon_assist/chat_ui.py`
  `rich`-based non-fullscreen chat rendering, including the `Sengent`
  welcome panel, user-message display, event stream blocks, and answer panels.

- `src/sentieon_assist/chat_events.py`
  Deterministic event-text helpers used by chat mode to describe real internal
  stages without pretending to have tool execution.

- `src/sentieon_assist/answering.py`
  Rule-first answer composition, source-backed model fallback, reference-query
  answering, and answer normalization.

- `src/sentieon_assist/llm_backends.py`
  Pluggable LLM backend router. Ollama remains the default primary backend, and
  an optional fallback backend can be attached without changing the CLI or
  answer pipeline.

- `src/sentieon_assist/ollama_client.py`
  Local Ollama HTTP client, non-stream generation, streaming generation, and
  model warmup.

- `src/sentieon_assist/classifier.py`
  Issue classification plus natural-reference-query detection.

- `src/sentieon_assist/extractor.py`
  Lightweight extraction for version, input type, error markers, and Chinese /
  mixed-language cues.

- `src/sentieon_assist/prompts.py`
  Prompt templates for support answers, chat rewrite/polish, and reference
  query synthesis.

- `src/sentieon_assist/doctor.py`
  Environment diagnostics for Ollama, knowledge packs, and source bundles.

- `src/sentieon_assist/knowledge/base/*.json`
  Bundled starter rules packaged with the library.

- `knowledge/base/*.json`
  Repo-root mirrors used for easier inspection/editing in the workspace.

- `sentieon-note/`
  Local curated notes used as the main evidence base at this stage.

## Reference Material Strategy

The project currently relies on the following local reference bundle:

- `sentieon-note/Sentieon202503.03.pdf`
- `sentieon-note/sentieon-modules.json`
- `sentieon-note/sentieon-module-index.md`
- `sentieon-note/sentieon-doc-map.md`
- `sentieon-note/sentieon-github-map.md`
- `sentieon-note/thread-019d5249-summary.md`
- `sentieon-note/sentieon-chinese-reference.md`

The assistant already exposes this through:

- `sources` for inventory
- `search` for keyword search
- module-index-first reference answers for major Sentieon modules
- source evidence collection for answer synthesis
- internal version/reference context for grounding and mismatch checks
- version mismatch warning when the query version differs from the mounted
  primary release
- compact user-facing reference answers that now hide internal trace sections
  such as `【资料查询】`, `【资料版本】`, and `【参考资料】`

## Milestones Completed

### Milestone 1: Offline MVP Harness

Completed:

- Python package scaffold and CLI entrypoint
- deterministic harness flow
- `license` and `install` rule packs
- structured extraction and state machine
- local source discovery and search
- environment doctor

### Milestone 2: Chinese-First Support Usability

Completed:

- Chinese and mixed-language issue classification
- Chinese version extraction in phrases such as `版本是202503.03`
- Chinese follow-up prompts like `Sentieon 版本`
- Chinese synonyms for `license/install` style queries

### Milestone 3: Natural Chat with Local Ollama

Completed:

- chat mode uses local Ollama for natural phrasing
- startup model availability check
- startup model warmup
- streaming model output
- `思考中...` status animation before each answer
- `OLLAMA_KEEP_ALIVE` config to reduce reload cost

### Milestone 4: Module Intro and Parameter Query Path

Completed:

- natural question routing for module intro / parameter lookup
- examples like `DNAscope 是做什么的`
- examples like `sentieon-cli dnascope 的 --pcr_free 是什么`
- deterministic parameter answers for indexed module flags before model fallback
- curated reference ranking so module/index files outrank generic PDF mentions
- local evidence first, local model organizes answer second

### Milestone 5: Pluggable LLM Backbone

Completed:

- Ollama remains the default primary backend
- new backend router isolates generation/probe/warmup from the CLI
- optional fallback backend skeleton now supported via config
- current supported fallback backend types:
  - `ollama`
  - `openai_compatible`

### Milestone 6: Chat UX and Reference Answer Cleanup

Completed:

- ambiguous parameter prompts are deterministic and no longer re-polished by
  the model
- chat can carry pending parameter-disambiguation context across turns
- repeated answers for the same parameter query are now stable
- user-visible reference answers hide internal trace/debug sections
- parameter answers are slimmer and now default to a compact
  `【常用参数】`-only presentation

### Milestone 7: Sengent Chat Shell

Completed:

- chat startup now renders a Chinese `Sengent` welcome panel every session
- chat remains non-fullscreen and continues to use normal terminal scrolling
- each turn now shows `你` -> `事件流` -> `Sengent`
- event stream output is deterministic and tied to real stages such as issue
  typing, missing-info checks, local source lookup, and reply generation
- prompt branding is now `Sengent>`

## Current Configuration

Main environment variables:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_KEEP_ALIVE`
- `SENGENT_LLM_FALLBACK_BACKEND`
- `SENGENT_LLM_FALLBACK_BASE_URL`
- `SENGENT_LLM_FALLBACK_MODEL`
- `SENGENT_LLM_FALLBACK_API_KEY`
- `SENTIEON_ASSIST_KNOWLEDGE_DIR`
- `SENTIEON_ASSIST_SOURCE_DIR`

Recommended local testing pattern:

```bash
cd /Users/zhuge/Documents/codex/harness
export PYTHONPATH=src
export OLLAMA_KEEP_ALIVE=30m
python3.11 -m sentieon_assist doctor
python3.11 -m sentieon_assist chat
```

## Remote Repository Context

The user provided a remote repository intended for ongoing project continuity:

- <https://github.com/freeword2020/sengent.git>

The local workspace at `/Users/zhuge/Documents/codex/harness` is now a git
worktree attached to that remote. Future threads should continue from this
repository directly unless there is a deliberate reason to move to a new
workspace.

## Recommended Next Milestones

Priority suggestions for future threads:

1. Expand parameter coverage beyond the current indexed set.
   Current high-frequency modules already covered:
   - `DNAscope`
   - `DNAscope LongRead`
   - `DNAscope Hybrid`
   - `Joint Call`
   - `GVCFtyper`
   - `TNscope`
   Next expansion targets:
   - `sentieon-cli` common global options
   - `DNAseq`
   - `CNVscope`
   - `RNAseq`
   - `GeneEditEvaluator`

2. Improve source-aware parameter answers for uncovered queries.
   Add value-based matching, richer per-parameter evidence, and better fallback
   ranking when a flag is not yet in the structured index.

3. Add explicit chat state introspection.
   The current chat carries pending follow-up context, but there is still no
   `/status` view for operators to inspect whether the system is waiting for a
   missing version, missing error text, or parameter-disambiguation module name.

4. Add explicit chat memory structure.
   The current chat carries pending follow-up context, but not a fuller
   multi-turn summary or conversation state object.

5. Add deployment documentation.
   A customer-site install guide, source bundle packaging guide, and model
   provisioning checklist will be needed for real rollout.

6. Add broader support domains.
   Candidates:
   - workflow selection
   - read-group issues
   - pangenome constraints
   - long-read support questions
   - common command/parameter explanation paths

## Verification Snapshot

Most recent verified state in this thread:

- full test suite passed
- `pytest -q`
- result: `103 passed in 4.26s`

## Immediate Handoff Notes

If a new thread continues from here, the most relevant current behavior is:

- `chat` prompt is `Sengent>`
- every `chat` session starts with a `Sengent` welcome panel
- each turn shows a lightweight event stream before the final answer block
- ambiguous parameters such as `--split_by_sample 是什么` now ask the user to
  confirm the module, and the next turn can be just `Joint Call`
- reference answers now intentionally hide internal trace blocks and show only
  user-facing content
- parameter answers are compact; module-intro answers still use
  `【模块介绍】`

Suggested next thread entry tests:

```bash
cd /Users/zhuge/Documents/codex/harness
export PYTHONPATH=src
export OLLAMA_KEEP_ALIVE=30m
python3.11 -m sentieon_assist chat
```

Then try:

- `DNAscope 是做什么的`
- `GVCFtyper 的 --genotype_model 是什么`
- `--split_by_sample 是什么`
- `Joint Call`

Future threads should re-run tests before claiming continuity.
