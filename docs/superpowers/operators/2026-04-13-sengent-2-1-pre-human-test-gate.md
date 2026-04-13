# Sengent 2.1 Pre-Human-Test Gate

This branch is a pre-human-test gate only. It is not a released product, and it must not be described or operated as customer-ready software.

Use this gate when you want to confirm that the hosted runtime path and the hosted factory-learning path are both configured, observable, and still separated by governance.

## runtime provider env/config

The runtime path is configured separately from the factory path.

- Set `SENGENT_RUNTIME_LLM_PROVIDER` first.
- For hosted runtime, set `SENGENT_RUNTIME_LLM_BASE_URL`, `SENGENT_RUNTIME_LLM_MODEL`, and `SENGENT_RUNTIME_LLM_API_KEY`.
- For Ollama-backed runtime, the code can fall back to `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_KEEP_ALIVE`.
- Keep the runtime capability flags explicit when needed: `SENGENT_RUNTIME_LLM_SUPPORTS_TOOLS`, `SENGENT_RUNTIME_LLM_SUPPORTS_JSON_SCHEMA`, `SENGENT_RUNTIME_LLM_SUPPORTS_REASONING_EFFORT`, `SENGENT_RUNTIME_LLM_SUPPORTS_STREAMING`, and `SENGENT_RUNTIME_LLM_MAX_CONTEXT`.
- Do not reuse the factory hosted variables to make runtime look healthy. Runtime health must stand on the runtime settings.

## factory provider env/config

Factory hosted drafting is configured on its own surface.

- Set `SENGENT_FACTORY_HOSTED_PROVIDER`, `SENGENT_FACTORY_HOSTED_BASE_URL`, `SENGENT_FACTORY_HOSTED_MODEL`, and `SENGENT_FACTORY_HOSTED_API_KEY`.
- Factory hosted can be disabled independently of runtime.
- If the factory provider is missing, the gate is still valid, but `doctor` should explain that hosted factory drafting is disabled.
- If the factory provider is present but misconfigured, fix it before any human test.
- Do not point the factory surface at the runtime surface just to avoid a separate review of the settings.

## doctor checks

Run `sengent doctor` on a host that is expected to answer questions.

Run `sengent doctor --skip-ollama` on a host that only builds, reviews, or activates knowledge.

Before a human test, confirm all of the following:

- `Runtime LLM` reports the expected provider, base URL, and model.
- `Factory Hosted` reports the expected provider, base URL, and model.
- The factory section says `mode: factory review-only`.
- `review_only: yes` is present for factory hosted.
- `managed_pack_complete` is `yes` when the source pack is meant to be fully active.
- `missing_managed_pack_files` and `invalid_managed_pack_files` are empty for a clean gate.

If `doctor` reports a clear remediation, fix the configuration first and rerun it. Do not hand-wave a bad doctor result into the human test.

## expected review-only behavior for factory drafts

Factory draft output is review material, not truth.

- `sengent knowledge factory-draft` must produce a draft that stays `needs_review`.
- Attached drafts should surface through `pending-factory-draft-review`.
- Review happens with `sengent knowledge queue` and `sengent knowledge review-factory-draft`.
- If factory hosted config is present and `--adapter` is omitted, the CLI may use the hosted adapter by default; pass `--adapter stub` only when you intentionally want the local stub path.
- The maintainer then copies accepted evidence back into inbox or metadata changes by hand.
- Standalone draft output created with `--output` does not automatically enter the maintainer queue.
- Factory drafts never auto-activate candidate packs and never change active packs directly.

## prohibited operations

Do not cross the governance boundary that keeps this branch safe for human testing.

- Do not promote factory draft output directly into runtime truth.
- Do not edit active packs from draft output.
- Do not skip review and activate a factory draft as if it were already approved.
- Do not treat factory review artifacts as released product behavior.
- Do not collapse runtime and factory provider configuration into one shared environment block.
- Do not turn this gate into customer packaging, rollout, or public release work.

## manual test categories

Use these manual test categories before handing the branch to a human tester.

- Runtime provider smoke: confirm `sengent doctor` and `sengent chat` behave as expected for the selected runtime provider.
- Factory provider smoke: confirm the factory provider is present or clearly disabled, and that the separate factory config is readable.
- Review-only smoke: confirm `sengent knowledge factory-draft --help` still describes an offline, review-needed path.
- Boundary smoke: confirm factory drafts remain review-only and cannot bypass `queue -> review-factory-draft -> manual edit`.
- Negative-path smoke: confirm missing runtime or factory settings produce clear remediation rather than silent fallback.

## pre-human-test smoke sequence

If real provider credentials and config clearly exist, run these live smokes:

```bash
PYTHONPATH=src python3.11 -m sentieon_assist doctor
PYTHONPATH=src python3.11 -m sentieon_assist chat
PYTHONPATH=src python3.11 -m sentieon_assist knowledge factory-draft --help
```

If credentials or config are not available, skip the live smokes and state that they were skipped because the provider setup was not present.

## gate output

At the end of this gate, report only the facts a maintainer needs to decide whether the branch is ready for structured human testing.

- Runtime provider reachable or clear provider-specific remediation.
- Factory provider configured separately from runtime, or clearly disabled with a remediation path.
- Factory draft path still review-only.
- No governance red lines were crossed.
- No release claim was made.
