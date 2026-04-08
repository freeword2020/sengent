# Harness System Handoff

This document is the closeout handoff after the deterministic reference
coverage expansion line was completed on `2026-04-08`. It is intended to be
the starting point for the next mainline focused on the harness system itself,
not another round of reference-content expansion.

## Current Closeout State

- Branch: `codex/reference-coverage-expansion`
- Draft PR: `#1`
- Head commit at closeout: `77e75e5`
- Latest full verification:
  - `python3.11 -m pytest -q` -> `258 passed in 28.33s`

## What This Line Delivered

The completed line now includes:

- deterministic coverage for common `sentieon-cli` global options such as `-t`
  and `-r`
- deterministic module-intro / parameter / script routing for the indexed
  Sentieon modules
- deterministic low-coverage boundary answers for `GeneEditEvaluator`
- deterministic workflow guidance for ambiguous `WGS` / `WES` / `panel` /
  `long-read` / `pangenome` questions
- deterministic follow-up normalization for short domain switches such as
  `那 panel 呢`, `那 long-read 呢`, `那配对呢`, `那无对照呢`, `那 FASTQ 呢`,
  `那 ONT 呢`, and contextual `hybrid` follow-ups
- deterministic escalation from converged workflow context to script skeleton
  for terse follow-ups such as `我就要个示例`
- external-reference coverage for common bioinformatics tools, file formats,
  and high-frequency error associations
- documentation and regression coverage for the full path above

## What Should Be Treated As Stable Boundaries

These boundaries were reinforced during this line and should stay in place
unless intentionally replaced:

1. Keep rule-first and deterministic routing as the default path.
2. Keep local curated references as the source of truth.
3. Do not reopen the chat-shell UI shape in the next thread.
4. Do not mix harness-system work with another broad reference-expansion wave.
5. Do not bypass tests; use `python3.11`, red-green-first, then targeted
   verification, then full `pytest -q`.

## What Hurt During This Cycle

The main process pain points were not product questions. They were harness
orchestration issues:

1. Reference-material work and harness-system work landed in the same branch
   for too long, which made the final diff larger than necessary.
2. Too much behavior still lives in `cli.py`, which currently carries chat
   loop control, reference-context reuse, follow-up normalization, and route
   orchestration together.
3. Deterministic routing rules now exist across multiple modules
   (`answering.py`, `reference_intents.py`, `workflow_index.py`,
   `external_guides.py`, `module_index.py`), but the ownership boundaries are
   only implicit.
4. Verification exists, but the suite is now large enough that the next line
   should group smoke checks and regression buckets more explicitly.

## Recommended Next Mainline: Harness System

The next mainline should focus on harness-system structure, not on more content
expansion. Recommended scope:

### 1. Split orchestration from presentation

Target:

- keep `chat_ui.py` focused on rendering
- keep `cli.py` focused on command entry and loop wiring
- move reference-context state and follow-up normalization into a narrower
  harness layer with explicit inputs and outputs

Why:

- this reduces regression risk when changing routing behavior
- it makes multi-turn deterministic behavior easier to test without full chat
  loop fixtures

### 2. Make deterministic route ownership explicit

Target:

- define a single route-order contract for:
  - module/parameter/script lookup
  - workflow guidance
  - external guides
  - external error associations
  - model fallback
- remove ambiguous overlap where two deterministic paths can both claim the
  same query

Why:

- current behavior is mostly correct, but the contract is spread across helper
  functions rather than one narrow decision surface

### 3. Normalize reference context as harness state

Target:

- make pending reference context, workflow context, and clarification context
  first-class state objects instead of ad hoc text-fragment checks spread
  through the chat loop

Why:

- this is the cleanest way to keep deterministic multi-turn behavior while
  avoiding more cue-patch growth

### 4. Add regression buckets for harness behavior

Target:

- keep full `pytest -q`
- add named targeted buckets for:
  - deterministic route selection
  - follow-up context reuse
  - external guide lookups
  - chat rendering/stable-markdown behavior

Why:

- the next thread should be able to run the right narrow checks while editing
  harness internals, then finish with the full suite

## Suggested Execution Order

1. Start from a fresh branch after the current PR is merged or otherwise
   settled.
2. Read `docs/project-context.md`, this handoff, and the merged diff for
   `codex/reference-coverage-expansion`.
3. Write a narrow harness-system plan before code changes.
4. First extract state/routing seams under tests.
5. Only after the seams are explicit, reduce `cli.py` responsibility.
6. Keep UI output and current user-visible chat shape unchanged unless a bug
   forces a surgical fix.

## Acceptance Criteria For The Next Harness Line

The next line should be considered successful only if:

- deterministic behavior stays unchanged for the current covered queries
- `cli.py` becomes meaningfully thinner in responsibility
- route precedence is documented and testable in one place
- multi-turn reference context handling is easier to reason about than it is
  now
- `python3.11 -m pytest -q` still passes at the end

## Suggested Starting Commands

```bash
cd /Users/zhuge/Documents/codex/harness
python3.11 -m pytest -q
git status --short
```

For targeted smoke during the next line:

```bash
PYTHONPATH=src python3.11 -m sentieon_assist.cli "我要做wgs分析，能给个示例脚本吗"
PYTHONPATH=src python3.11 -m sentieon_assist.cli "短读长胚系二倍体"
PYTHONPATH=src python3.11 -m sentieon_assist.cli "我就要个示例"
PYTHONPATH=src python3.11 -m sentieon_assist.cli "VCF 报 contig not found 是什么情况"
```

## Final Note

Do not treat the next phase as another content-harvest round. The current
reference surface is broad enough for now. The next mainline should spend its
budget on harness-system shape, route ownership, state clarity, and regression
discipline.
