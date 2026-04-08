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
- installed package dependencies now include `rich` for chat-mode terminal rendering

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
- `sentieon-note/workflow-guides.json`
- `sentieon-note/external-format-guides.json`
- `sentieon-note/external-tool-guides.json`
- `sentieon-note/external-error-associations.json`

## Example usage

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "Sentieon 202503 license 报错，找不到 license 文件"
```

```bash
OLLAMA_MODEL=gemma4:e4b PYTHONPATH=src python3.11 -m sentieon_assist.cli "Sentieon 202503 install 失败，解压后命令不可用"
```

For customer-site testing without changing shell environment:

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli \
  --knowledge-dir /path/to/customer-knowledge \
  --source-dir /path/to/customer-sources \
  "Sentieon 202503 install 失败，解压后命令不可用"
```

## Interactive terminal mode

```bash
PYTHONPATH=src python3.11 -m sentieon_assist chat
```

Then enter questions one by one. Use `/quit` to exit.

Current chat behavior:

- every session starts with a Chinese `Sengent` welcome panel
- the welcome panel now uses a pixel-style `SENGENT` logo on the left and a compact capability summary on the right
- the chat shell is still non-fullscreen; it remains a normal scrolling terminal session
- the interactive prompt is branded as `Sengent>` and uses ANSI emphasis on real TTY terminals
- each turn now shows a single-line `正在思考中...` status before answer output starts
- model-backed turns stream progressively when Ollama returns chunks
- chat startup warms up the local model to reduce first-turn latency
- final answers render as a `Sengent` answer block or a streaming `Sengent` rule header
- stable boundary/reference answers skip unnecessary re-polish and are normalized before display so raw Markdown markers do not leak into the terminal
- rule-first answers remain the backbone; the local model mainly handles natural follow-up wording and answer polishing

## Environment doctor

Use the built-in doctor command before customer-site troubleshooting:

```bash
PYTHONPATH=src python3.11 -m sentieon_assist doctor
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
PYTHONPATH=src python3.11 -m sentieon_assist --source-dir /path/to/customer-sources sources
```

The source list shows a trust tier:

- `official`: primary source, such as the local Sentieon release PDF
- `derived`: internal summaries, maps, and curated notes
- `secondary`: helpful but lower-priority references such as the Chinese overview

Search local reference materials by keyword:

```bash
PYTHONPATH=src python3.11 -m sentieon_assist --source-dir /path/to/customer-sources search SENTIEON_LICENSE
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
PYTHONPATH=src python3.11 -m sentieon_assist.cli "DNAscope 是做什么的"
```

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "sentieon都有哪些模块"
```

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "sentieon-cli dnascope 的 --pcr_free 是什么"
```

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "能给个 rnaseq 的参考脚本吗"
```

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "sentieon-cli 的 -t 是什么"
```

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "GeneEditEvaluator 的参数有哪些"
```

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "能给个 GeneEditEvaluator 的参考脚本吗"
```

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "如果我要做wgs分析，能不能给个指导"
```

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "VCF 的 INFO 和 FORMAT 有什么区别"
```

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "VCF 报 contig not found 是什么情况"
```

The assistant answers these by preferring mounted local notes and source
snippets. For module-intro questions and the currently indexed high-frequency
parameter questions, it now prefers the curated module index first and answers
them deterministically before involving the model. This deterministic coverage
now also includes common `sentieon-cli` / `sentieon driver` global options such
as `-t` and `-r`. Uncovered parameter/detail questions still fall back to local
source evidence. Module overview questions such as `sentieon都有哪些模块` are
semantically routed through a lightweight intent parser, then answered
deterministically from the module index. Script / reference-command questions
now use the same semantic routing path and return indexed command skeletons for
`RNAseq`, `DNAseq`, `DNAscope`, `DNAscope LongRead`, `DNAscope Hybrid`,
`Sentieon Pangenome`, `CNVscope`, `TNscope`, and `Joint Call`. For
`GeneEditEvaluator`, the current mounted official materials only provide a
release-note-level mention, so intro / parameter / script questions now return
deterministic coverage-boundary answers instead of falling straight back to the
model. In chat mode, reference follow-up context can now carry across turns for
clearly reference-related short continuations such as asking about `RNAseq`
first and then following with `示例脚本也可以` or `参数呢`. The stable reference
display path also normalizes a small set of bioinformatics terms into
Chinese-first phrasing with English anchors, so outputs such as
`matched normal`, `tumor-only`, and `germline variants` read more naturally in
customer-facing Chinese answers. Chat follow-up reuse now also covers short
workflow-domain switches such as `那 panel 呢` or `那 long-read 呢`, so these
turns stay on the deterministic reference path instead of first paying the
intent-model latency. By contrast, vague deictic fragments such as `那这个呢`
are intentionally kept out of automatic reference-context reuse and now fail
fast locally without first calling the model. If the module is already known
but the user only says `这个参数呢`, the assistant now returns a deterministic
parameter-name clarification with indexed examples such as `--pcr_free` or
`-t`, instead of falling through to the model. WGS follow-ups like `那胚系呢`
also now resolve to a dedicated germline-WGS split rather than the generic WGS
guidance block. Somatic WGS fragments such as `那配对呢`, `那有对照呢`, and
`那无对照呢` are now canonicalized locally to paired/unpaired somatic follow-up
forms and land on dedicated WGS guidance instead of the generic WGS answer. The
same normalization now carries `WES` and `panel` context too, so paired or
unpaired short follow-ups after those workflow questions resolve to dedicated
somatic WES/panel guidance rather than generic somatic routing. The same
deterministic follow-up normalizer now also covers input-shape fragments such
as `那 FASTQ 呢`, `那 BAM 呢`, and `那 CRAM 呢` under existing `WGS` / `WES` /
`panel` context, plus long-read platform fragments such as `那 ONT 呢` and
`那 HiFi 呢` under existing `long-read` context. These short turns resolve from
dedicated workflow-guide entries instead of dropping back to the model, while
vague format/platform fragments such as `这个格式呢` or `这个平台呢` remain
outside automatic context reuse. Semantic workflow fragments such as
`那体细胞呢`, `那肿瘤的呢`, and `那胚系呢` now also normalize locally, so `WES`
and `panel` follow-up turns can land on dedicated somatic/germline workflow
guidance before the more specific paired/unpaired split is known. For `WGS`
threads, `那短读长呢` / `那 short-read 呢` now also resolve to a dedicated
short-read WGS intermediate guidance block instead of falling back to the
fully generic WGS ambiguity answer. The same short-read semantic follow-up
layer now also covers `WES` and `panel`, so these turns no longer overcommit
to germline WES or stay stuck at generic panel routing before the
germline/somatic branch is known. Contextual `hybrid` follow-ups such as
`那 hybrid 呢`, `那联合分析呢`, or `那 short-read + long-read 呢` now also stay
on the deterministic workflow-guidance path under existing workflow context,
while standalone `DNAscope Hybrid` script requests still return the deterministic
reference command skeleton.

Mounted external-reference coverage is now split into three explicit layers:

- external format guides for stable structure/field/index explanations such as
  `VCF/BCF`, `SAM/BAM/CRAM`, `Read Group`, `BED/interval`, and `FASTA/FAI`
- external tool guides for stable tool/report explanations such as `samtools`,
  `bcftools`, `FastQC`, `MultiQC`, `bgzip/tabix`, `grep`, `sed`, `awk`, and
  shell quoting / pipeline basics
- external error associations for high-frequency format/tool error attribution
  such as `bgzip/tabix` indexing mismatch, `Read Group/header` inconsistency,
  `CRAM/reference` mismatch, `CRAM/CRAI` random-access state, `contig naming`
  mismatch, `BED` coordinate-system mismatch, `FASTA/FAI/dict` companion
  mismatch, `BAM sort/index` state, and shell quoting / `grep` / `sed` / `awk`
  misuse

These external layers are secondary evidence only. They explain format/tool
structure and say which layer should be checked first, but they do not replace
Sentieon official workflow or module conclusions.

For compact customer-facing output:

- module intro questions still show `【模块介绍】`
- parameter questions now prefer a shorter `【常用参数】` answer
- known low-coverage modules such as `GeneEditEvaluator` now return explicit
  boundary text instead of ad-hoc model completions
- ambiguous parameter names first ask the user to confirm the module, then
  continue on the next turn

## Recommended Local Testing

```bash
export PYTHONPATH=src
export OLLAMA_KEEP_ALIVE=30m
python3.11 -m sentieon_assist doctor
python3.11 -m sentieon_assist chat
```
