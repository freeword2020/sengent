# Knowledge Packs

This directory stores external knowledge files for the Sentieon support harness.

## Layout

- `base/`
  - bundled starter knowledge packs
- future customer-site overrides may live beside or above this directory

## Update model without code changes

Change:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`

The application must not require code edits for a model swap.

## Add a new Sentieon version-specific pack

Create a new JSON rule file with version-aware guidance and load it through the
knowledge layer instead of hardcoding the content in Python modules.

## Customer-site overrides

Customer deployments should be able to replace or extend the bundled base
knowledge files with site-specific rule packs, SOPs, and version notes.
