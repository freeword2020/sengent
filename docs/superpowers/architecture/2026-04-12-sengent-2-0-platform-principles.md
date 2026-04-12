# Sengent 2.0 Platform Principles

## Boundary

`Sengent 2.0` is a `support kernel`, not a vendor-specific assistant. A `vendor profile` supplies facts, workflows, and limits; the kernel supplies the rules that every profile must obey.

## Kernel Rules

- Use an `evidence hierarchy` before answering: active vendor packs, domain standards, playbooks, incident memory, then current session context.
- Follow `证据不足时先澄清` when the evidence is incomplete.
- Enforce an `answer contract`: state the current best answer, what is known, what is uncertain, and the next action.
- Keep a `controlled learning loop` inside the kernel: capture gaps, route them to review, and never mutate runtime behavior directly from one-off conversations.

## Durable Constraint

The kernel must stay profile-agnostic. New software support adds or replaces a `vendor profile`; it does not rewrite the support kernel.
