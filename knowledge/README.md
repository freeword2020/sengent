# Knowledge Packs

This directory contains bundled base rule packs that ship with Sengent.

## What Lives Here

- `base/`
  - bundled starter rule packs used by the runtime knowledge layer

These files are part of the packaged application surface, not the normal maintainer renew workflow.

## Important Boundary

Normal maintainers should **not** treat this directory as the primary place to edit Sentieon knowledge.

For routine knowledge updates, use:

1. `sengent knowledge scaffold`
2. `sengent knowledge build`
3. `sengent knowledge review`
4. gate
5. `sengent knowledge activate`
6. `sengent knowledge rollback` if needed

## What This Directory Is For

Use `knowledge/base/` for:

- bundled starter rules
- packaged defaults
- code-shipped knowledge behavior that must exist even without customer-specific source bundles

## What This Directory Is Not For

Do not use `knowledge/base/` as a shortcut for:

- hand-editing active source packs
- bypassing scaffold/build/review/gate/activate
- customer-site one-off content drops

## Model Configuration Boundary

Model changes are configuration, not knowledge-pack edits.

Change:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`

Do not require Python code edits or direct JSON pack edits just to swap a model.
