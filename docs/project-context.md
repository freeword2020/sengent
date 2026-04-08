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
- a startup poster-style welcome panel and branded `Sengent>` prompt
- streaming output in chat with a visible `正在思考中...` status line
- natural local reference queries for Sentieon modules and common parameters
- semantic reference routing for module overview and reference-script questions
- deterministic workflow-guidance routing for ambiguous WGS/WES/panel/long-read
  questions and their short follow-ups
- deterministic script-answer coverage for the current indexed high-frequency modules
- deterministic answers for common `sentieon-cli` global options such as `-t`
  and `-r`
- deterministic low-coverage boundary answers for `GeneEditEvaluator` intro /
  parameter / script questions
- secondary external-reference coverage for common bioinformatics
  format/tool questions
- deterministic external error-association answers for high-frequency
  format/tool mismatches such as `bgzip/tabix`, `Read Group`, `CRAM/reference`,
  `contig naming`, `BED` coordinate semantics, `FASTA/FAI/dict` companion
  files, and `BAM sort/index` state

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
  welcome panel, pixel-style logo poster, streaming header, and answer panels.

- `src/sentieon_assist/chat_events.py`
  Deterministic status-text helpers used by chat mode for transient labels such
  as reply generation.

- `src/sentieon_assist/answering.py`
  Rule-first answer composition, source-backed model fallback, reference-query
  answering, and answer normalization.

- `src/sentieon_assist/reference_intents.py`
  Lightweight semantic reference-intent parsing for module, parameter, script,
  workflow-guidance, and external-reference questions.

- `src/sentieon_assist/workflow_index.py`
  Deterministic workflow-guide lookup against the structured workflow index.

- `src/sentieon_assist/external_guides.py`
  Structured lookup and formatting for external format/tool guides and
  high-frequency external error associations.

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
- `sentieon-note/workflow-guides.json`
- `sentieon-note/sentieon-module-index.md`
- `sentieon-note/sentieon-script-index.md`
- `sentieon-note/sentieon-doc-map.md`
- `sentieon-note/sentieon-github-map.md`
- `sentieon-note/external-format-guides.json`
- `sentieon-note/external-tool-guides.json`
- `sentieon-note/external-error-associations.json`
- `sentieon-note/external-format-reference.md`
- `sentieon-note/external-tool-reference.md`
- `sentieon-note/external-error-reference.md`
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
- `正在思考中...` status animation before each answer
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
- the left side of the welcome panel now uses a pixel-style `SENGENT` logo
- prompt branding is now `Sengent>` with stronger emphasis on interactive TTYs
- answer output is rendered as `Sengent` blocks / streaming headers instead of
  a plain `print` transcript
- the mainline shell intentionally dropped separate `你` / `事件流` panes to
  stay closer to a Claude-Code-like command-line rhythm

### Milestone 8: Semantic Reference Routing

Completed:

- reference questions no longer rely only on hand-written cue matching
- a lightweight Ollama-backed intent parser now identifies at least:
  - module overview questions
  - script / reference-command questions
- deterministic module overview answers are available for queries such as:
  - `sentieon都有哪些模块`
  - `有哪些主要模块`
- indexed script answers are now available for:
  - `RNAseq`
  - `DNAseq`
  - `DNAscope`
  - `DNAscope LongRead`
  - `DNAscope Hybrid`
  - `Sentieon Pangenome`
  - `CNVscope`
  - `TNscope`
  - `Joint Call`

### Milestone 9: Mainline Tightening and Display Cleanup

Completed:

- reference answers can now carry script / parameter follow-up context across
  turns when the user asks a natural short continuation
- chat pre-answer status is unified to `正在思考中...` rather than exposing
  different internal labels such as source-search text
- stable chat answers are normalized before display, so raw Markdown markers
  such as `**`, leading `*`, and backticks do not leak into the terminal
- boundary replies such as the current MVP support scope remain fast and skip
  unnecessary model re-polish

### Milestone 10: Reference Coverage Expansion

Completed:

- deterministic parameter answers now cover common `sentieon-cli` / `sentieon driver`
  global options such as `-t` and `-r`
- `GeneEditEvaluator` now has deterministic release-note-only coverage for:
  - module intro
  - parameter-status questions
  - script-status questions
- short chat follow-ups now reuse prior reference context only when the follow-up
  is clearly reference-related, avoiding over-eager context carry from vague
  `reference_other` turns

### Milestone 11: Workflow Guidance and External Reference Layer

Completed:

- deterministic workflow-guidance answers now cover ambiguous `WGS`, `WES`,
  `panel`, `long-read`, `tumor-normal`, `tumor-only`, and contextual `hybrid`
  follow-up queries without falling back to module lists
- external-reference coverage is now split into:
  - external format guides
  - external tool guides
  - external error associations
- high-frequency external error-association coverage now includes:
  - `bgzip/tabix` indexing mismatch
  - `Read Group/header` inconsistency
  - `CRAM/reference` mismatch
  - `contig naming / sequence dictionary` mismatch
  - `BED / interval` coordinate-system mismatch
  - `FASTA/FAI/dict` companion mismatch
  - `BAM sort/index` state mismatch
  - `CRAM/CRAI` random-access state mismatch
  - shell quoting / pipeline syntax
  - `grep` regex vs fixed-string mismatch
  - `sed` quoting / in-place misuse
  - `awk` field-separator / shell-expansion mismatch
- explanatory external queries such as `VCF 的 INFO 和 FORMAT 有什么区别`
  now stay on the normal external-guide path instead of being polluted by the
  error-association layer
- external matcher hardening now avoids raw substring collisions such as `sam`
  inside `sample`, requires `VCF/BCF` context for bare `INFO/FORMAT`, and keeps
  explicit Sentieon module queries ahead of generic external-guide hits
- Sentieon workflow/module conclusions remain isolated from this external
  secondary-evidence layer

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

1. Expand deterministic reference coverage beyond the current indexed set.
   Current high-frequency modules already covered:
   - `DNAscope`
   - `DNAseq`
   - `DNAscope LongRead`
   - `DNAscope Hybrid`
   - `Sentieon Pangenome`
   - `CNVscope`
   - `Joint Call`
   - `GVCFtyper`
   - `TNscope`
   - `RNAseq`
   Next expansion targets:
   - cross-module shared flags
   - more deterministic script coverage where the local bundle has stable usage text
   - broader `sentieon driver` shared flags beyond `-t` / `-r`
   - more low-coverage boundary entries like `GeneEditEvaluator` where the local
     official bundle only has release-note-level mentions

2. Improve source-aware parameter answers for uncovered queries.
   Add value-based matching, richer per-parameter evidence, and better fallback
   ranking when a flag is not yet in the structured index.

3. Add chat latency and timeout guardrails.
   The current shell is visually stable, but a slow local Ollama response can
   still leave operators staring at `正在思考中...` for too long without an
   explicit timeout, retry, or degradation path.

4. Add explicit chat state introspection.
   The current chat carries pending follow-up context, but not a fuller
   operator-visible `/status` view or multi-turn summary object.

5. Add deployment documentation.
   A customer-site install guide, source bundle packaging guide, and model
   provisioning checklist will be needed for real rollout.

6. Add broader support domains.
   Candidates:
   - customer-facing install/package deployment notes
   - richer pangenome and non-diploid constraints
   - more high-frequency external support diagnostics beyond the current
     format/tool set
   - common command/parameter explanation paths that still lack stable local
     evidence

Current implementation handoff for the next active phase:

- `docs/superpowers/plans/2026-04-08-reference-coverage-expansion.md`
- `docs/superpowers/plans/2026-04-08-high-frequency-error-association.md`

## Verification Snapshot

Most recent verified state in this thread:

- full test suite passed
- `pytest -q tests/test_answering.py tests/test_classifier.py tests/test_sources.py tests/test_reference_intents.py tests/test_cli.py tests/test_llm_backends.py`
- result: `219 passed in 79.15s`
- real chat smoke passed for:
  - `VCF 报 contig not found 是什么情况`
  - `VCF 的 INFO 和 FORMAT 有什么区别`
  - `如果我要做wgs分析，能不能给个指导`
  - `bash 的引号和管道怎么用`
  - `bash 报 unexpected EOF while looking for matching quote`
  - `DNAscope 的 bash 脚本`

## Immediate Handoff Notes

If a new thread continues from here, the most relevant current behavior is:

- `chat` prompt is `Sengent>`
- every `chat` session starts with a `Sengent` welcome panel
- the welcome panel now uses a pixel-style `SENGENT` logo and a compact summary
- each turn shows a lightweight `正在思考中...` status before the final answer
  block
- ambiguous parameters such as `--split_by_sample 是什么` now ask the user to
  confirm the module, and the next turn can be just `Joint Call`
- reference answers now intentionally hide internal trace blocks and show only
  user-facing content
- stable displayed answers now scrub leaked Markdown markers before rendering
- parameter answers are compact; module-intro answers still use
  `【模块介绍】`
- `sentieon-cli 的 -t / -r` now resolve deterministically from the structured
  local bundle
- `GeneEditEvaluator` intro / parameter / script questions now stay deterministic
  and explicitly report the current local-bundle coverage boundary
- short follow-ups only reuse prior reference context when they are clearly
  asking for more reference detail
- deterministic reference answers now normalize a small set of
  bioinformatics-industry terms into stable Chinese-first phrasing with English
  anchors, such as `matched normal`, `tumor-only`, and `germline variants`
- short workflow-domain follow-ups such as `那 panel 呢` or `那 long-read 呢`
  now also reuse prior reference context without first calling the local model
- deictic short follow-ups such as `那这个呢` remain intentionally outside
  automatic reference-context reuse, and now short-circuit to `False` locally
  instead of first probing the intent model
- module-known deictic parameter follow-ups such as `介绍下 dnascope` ->
  `这个参数呢` now return a deterministic parameter-name clarification instead
  of falling through to the model
- WGS follow-ups such as `那胚系呢` now resolve to a dedicated germline-WGS
  workflow split rather than dropping back to the generic WGS guidance block
- somatic WGS fragments such as `那配对呢` / `那有对照呢` / `那无对照呢`
  now canonicalize locally to `tumor-normal` / `tumor-only` and resolve to
  dedicated paired/unpaired WGS workflow guidance
- the same paired/unpaired follow-up normalization now also carries WES and
  panel context, so `那配对呢` / `那无对照呢` after WES or panel questions land
  on dedicated somatic WES/panel guidance instead of generic somatic answers
- short input-shape follow-ups such as `那 FASTQ 呢` / `那 BAM 呢` / `那 CRAM 呢`
  now also reuse existing WGS/WES/panel reference context and resolve to
  dedicated input-specific workflow guidance without first calling the local
  model
- short long-read platform follow-ups such as `那 ONT 呢` / `那 HiFi 呢` now
  resolve to dedicated platform-specific long-read guidance instead of the
  generic long-read block
- short semantic workflow follow-ups such as `那体细胞呢` / `那肿瘤的呢` /
  `那胚系呢` now also canonicalize locally and reuse existing `WES` / `panel`
  reference context, resolving to dedicated somatic/germline workflow guidance
  instead of falling back to generic WES/panel blocks
- `WGS` follow-ups such as `那短读长呢` / `那 short-read 呢` now resolve to a
  dedicated short-read-WGS intermediate guidance block, which keeps the answer
  narrower than the generic WGS ambiguity block while still asking for
  germline vs somatic confirmation
- `WES` / `panel` follow-ups such as `那 short-read 呢` / `那短读长呢` now also
  resolve to dedicated short-read intermediate guidance blocks, so the answer
  no longer jumps straight to short-read germline WES or stays at the generic
  panel block before the germline/somatic split is known
- contextual `hybrid` follow-ups such as `那 hybrid 呢` / `那联合分析呢` /
  `那 short-read + long-read 呢` now prefer dedicated workflow guidance under
  existing `WGS` / `long-read` context instead of jumping straight to the
  `DNAscope Hybrid` script/module answer
- standalone `DNAscope Hybrid` script requests remain on the deterministic
  script-example path; only contextual workflow follow-ups are re-routed
- vague format/platform deictics such as `这个格式呢` / `这个平台呢` remain
  intentionally outside automatic context reuse unless the fragment itself
  contains a recognized high-signal deterministic cue
- external format/tool questions such as `VCF 的 INFO 和 FORMAT 有什么区别`
  now stay on the normal external-guide path and do not accidentally pick up
  external error-association output
- high-frequency external error questions such as `VCF 报 contig not found
  是什么情况` or `BAM 不能随机访问，是不是没排序或者没索引` now return
  deterministic `【关联判断】` / `【优先检查】` answers from the local secondary
  evidence layer
- shell-oriented secondary queries such as `bash 的引号和管道怎么用` or
  `bash 报 unexpected EOF while looking for matching quote` now route to local
  external guides / error associations, while explicit Sentieon module queries
  like `DNAscope 的 bash 脚本` still stay on the Sentieon reference path
- placeholder modules tagged as `待核验占位` now prefer explicit coverage-boundary
  answers even if an intent model guesses `parameter_lookup`

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
- `sentieon-cli 的 -t 是什么`
- `VCF 的 INFO 和 FORMAT 有什么区别`
- `VCF 报 contig not found 是什么情况`
- `如果我要做wgs分析，能不能给个指导`
- `GeneEditEvaluator 的参数有哪些`

Future threads should re-run tests before claiming continuity.
