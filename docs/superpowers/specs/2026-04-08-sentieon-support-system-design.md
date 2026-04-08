# Sentieon Support System Design

## Context

The current harness drifted into three overlapping product identities:

- a `license/install` troubleshooter
- a reference lookup shell for modules, parameters, and scripts
- an open-ended Sentieon chat assistant

That drift created unstable routing. Slight wording changes can push the same
user need onto different code paths, which then produce contradictory or
misleading answers. Examples observed in the current system:

- broad capability questions fall back to `当前 MVP 仅支持 license 和 install 问题`
- `介绍下 AlignmentStat` routes to the `Alignment` family instead of the
  `AlignmentStat` QC submodule
- multi-turn workflow/script follow-ups depend on text concatenation rather
  than explicit task state

The redesign in this document re-anchors the product as a conservative,
single-entry Sentieon technical support assistant.

## Product Definition

The first customer-facing version of `Sengent` must do exactly four things:

1. onboard users into the Sentieon product surface
2. troubleshoot customer problems
3. identify the user’s actual support task precisely
4. give correct next-step guidance grounded in local rules and references

The system is not an open-ended general chat assistant. It is a support
assistant with bounded responsibilities.

### In Scope

- troubleshooting installation, license, runtime, file-format, and common
  workflow mismatch problems
- onboarding and workflow navigation such as `WGS/WES/panel 怎么选`
- reference lookup for modules, parameters, inputs, outputs, and script
  skeletons
- capability explanation and guidance when the user asks broad or ambiguous
  support questions

### Out of Scope

- unconstrained encyclopedia-style Sentieon conversation
- answering broad questions by guessing through model prose when routing is
  ambiguous
- treating UI polish as a substitute for support correctness

## Core Product Contract

The support assistant exposes one entrypoint and four support task classes:

1. `troubleshooting`
2. `onboarding_guidance`
3. `reference_lookup`
4. `capability_explanation`

### Route Priority

The route coordinator must apply a fixed priority order:

1. `troubleshooting`
2. `onboarding_guidance`
3. `reference_lookup`
4. `capability_explanation`

This order reflects the product identity:

- users with a broken environment should not be diverted into reference prose
- users asking how to start should be guided before being dumped into raw
  module details
- reference lookup supports the first two tasks, but does not define the
  product on its own
- broad or ambiguous prompts must result in capability explanation or
  clarification, not the old MVP fallback

### Conservative Clarification Rule

When the system cannot confidently place a user request into a single task
class, it must ask a clarification question instead of guessing.

Examples:

- `能给个 WES 示例吗` without germline/somatic context should clarify before
  emitting a script
- `这个报错怎么修` without error text should clarify before diagnosing
- `你能做什么` should explain supported help types and offer the next step

## Session State Model

The current harness relies on raw text reuse (`pending_query`,
`reference_context_query`) and heuristics that concatenate prior turns. That is
too weak for customer support.

The redesigned session state must carry explicit structured state:

### 1. Active Support Task

Exactly one of:

- `troubleshooting`
- `onboarding_guidance`
- `reference_lookup`
- `capability_explanation`

### 2. Confirmed Facts

Structured facts extracted from the user’s answers.

Troubleshooting examples:

- Sentieon version
- failing step
- exact error text
- input file type
- workflow/data type

Guidance examples:

- WGS / WES / panel / RNA / long-read / pangenome
- germline / somatic
- diploid / non-diploid
- FASTQ / uBAM-uCRAM / BAM-CRAM input shape

Reference examples:

- module name
- parameter name
- request type (`intro`, `inputs`, `outputs`, `parameter`, `script`)

### 3. Open Clarification Slots

The state must explicitly track which slots are still required before a safe
answer can be given.

Examples:

- troubleshooting: missing exact error text
- onboarding: missing germline vs somatic
- reference lookup: missing concrete module or parameter

### 4. Last Route Decision

Each turn should record why the previous route was chosen so the next turn can
distinguish:

- answer to a clarification question
- refinement within the same task
- explicit task switch

The system must stop encoding state by blindly appending raw user text to the
previous query.

## Architecture

### Support Coordinator

Add a single top-level coordinator responsible for:

- classifying the current turn into one support task
- deciding whether to clarify, answer, or switch tasks
- preserving the fixed route order
- returning both the route decision and the state transition

This replaces the current overlapping entry behavior where `classify_query`,
`is_reference_query`, and `parse_reference_intent` can each claim the turn.

### Task Engines

The coordinator delegates to bounded task engines:

- `Troubleshooting Engine`
- `Onboarding Guidance Engine`
- `Reference Lookup Engine`
- `Capability Explanation Engine`

Each engine receives:

- the normalized user turn
- the current session state
- extracted structured facts

Each engine returns:

- answer text or clarification text
- updated facts
- unresolved clarification slots
- whether the route should stay active for the next turn

### Presentation Boundary

`chat_ui.py` remains a rendering-only layer.

`cli.py` keeps:

- command parsing
- chat loop wiring
- model warmup
- status rendering hooks

`cli.py` must stop owning support semantics such as:

- route precedence
- context concatenation rules
- ad hoc reference-followup normalization

### Match Quality Rules

Reference and module matching must move from “best substring win” toward
support-safe matching:

1. exact module name and exact alias matches first
2. token-boundary matches next
3. family/group fallbacks only when no concrete submodule is matched

This prevents `AlignmentStat` from collapsing into the `Alignment` family and
keeps customer-facing explanations precise.

## User Experience Rules

### Capability Questions

Broad support questions such as:

- `你能做什么`
- `你不是可以提供 Sentieon 的功能吗`
- `你能为我做些说明`

must enter `capability_explanation`, not the old MVP fallback.

The answer should:

- explain supported help types briefly
- tell the user what information makes support faster
- invite the next concrete step

### Troubleshooting

Troubleshooting responses should prioritize:

1. task identification
2. missing evidence collection
3. likely root cause categories
4. next actionable checks

### Onboarding Guidance

Onboarding answers should prioritize:

1. identifying the user’s data/problem shape
2. guiding them to the right workflow/module family
3. naming missing decisions
4. handing off to reference/script lookup only when the route is sufficiently
   narrowed

### Reference Lookup

Reference answers should stay compact and precise:

- module introduction
- parameter meaning
- inputs/outputs
- script skeletons

If the requested entity is ambiguous or unavailable, the system should state
that boundary explicitly instead of fabricating a broader answer.

## Phase 1 Implementation Scope

This redesign should be delivered in a narrow first phase focused on harness
structure, not another content expansion wave.

Phase 1 includes:

- introducing structured support session state
- introducing a single support coordinator
- moving chat follow-up/context reuse decisions out of raw string concatenation
- routing broad capability questions to a dedicated capability explanation path
- hardening module matching to avoid family/submodule collisions
- preserving existing `rich` UI shape and existing deterministic answer content
  where already correct

Phase 1 does not include:

- redesigning the welcome panel aesthetics
- adding new large reference bundles
- broadening the product into general Q&A

## Acceptance Criteria

The redesign is acceptable only if the following hold:

1. broad capability prompts no longer fall back to `当前 MVP 仅支持 license 和
   install 问题`
2. `AlignmentStat`-style concrete submodule prompts do not degrade into broader
   family summaries
3. multi-turn clarification flow uses explicit state and does not rely on blind
   query concatenation
4. route precedence is implemented in one place and is testable directly
5. existing deterministic coverage for supported reference and troubleshooting
   queries remains intact
6. `python3.11 -m pytest -q` passes after implementation

## Test Strategy

Add and maintain named regression buckets for:

- support route selection
- clarification flow and state reuse
- module/entity resolution precision
- chat rendering stability

The initial implementation should also add explicit regression cases for the
real failure examples that motivated this redesign.
