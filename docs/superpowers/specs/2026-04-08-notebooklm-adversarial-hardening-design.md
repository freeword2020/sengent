# NotebookLM Adversarial Hardening Design

## Goal

Use the 50 NotebookLM adversarial prompts as a support-system hardening set, not as a promise to answer every Sentieon-adjacent question. The first-stage material is sufficient for current route/refactor work, but not sufficient for deterministic answers to benchmark-heavy, competitive, roadmap, or exact numeric claims.

## Design Decision

`Sengent` stays a conservative Sentieon technical support assistant. For this stage:

- keep strong support for onboarding guidance, troubleshooting, module lookup, parameter lookup, and supported workflow/script navigation
- stop using free-form model fallback for deep mechanism, benchmark, competitive, cost, and roadmap prompts that are not backed by structured support coverage
- convert the 50 prompts into an executable adversarial corpus with an expected behavior per prompt

The system should prefer:

1. deterministic supported answer
2. deterministic clarification
3. deterministic boundary answer

It should not jump from sparse snippets to confident technical claims.

## Coverage Judgment

### A. Relevant and sufficiently grounded for current-stage hardening

These are either already covered by the current source bundle or close enough that they belong in the current support scope:

- 1. architecture / hardware compatibility
- 2. CLI install and `sentieon-cli` packaging
- 3. `LICSRVR` / `LICCLNT`
- 4. `sentieon driver` vs `sentieon-cli`
- 5. `Too many open files` / `ulimit -n`
- 6. `samtools collate` vs FASTQ dump path
- 7. BWA `shm`
- 10. interleaved FASTQ and `-p`
- 12. `LocusCollector` + `Dedup`
- 14. `QualCal` / BQSR role
- 15. QC algorithms and `driver --algo`
- 17. model bundle download / platform family matching
- 19. PCR-free / `--pcr_indel_model none`
- 21. `GVCFtyper --emit_mode`
- 25. TNscope multi-class calling scope
- 26. contamination / orientation bias into filtering
- 28. UMI consensus quality retention
- 30. long-read platform support
- 32. `VariantPhaser`
- 33. Hybrid is not simple union
- 34. Hybrid responsibility split by data type
- 38. pangenome lift-over back to GRCh38
- 44. short-read SV vs long-read SV positioning
- 45. `SVSolver`
- 49. `LongReadUtil`

### B. Relevant, but current structured support coverage is not yet strong enough

These questions are still in product scope, but the current local bundle is too weak or too unstructured for deterministic support answers:

- 11. Sentieon STAR vs STAR / STARsolo / CellRanger acceleration
- 13. UMI consensus error-correction principle
- 16. Haplotyper vs DNAscope algorithmic evolution
- 20. VQSR vs `DNAModelApply`
- 23. trio two-pass / `bcftools trio-dnm2`
- 24. somatic caller differences plus low-frequency sensitivity ranking
- 29. `TNModelApply` artifact classes for FFPE / target capture
- 37. pangenome K-mer personalization path
- 42. CNVscope smallest reliably detected event size
- 43. CNVscope segmentation / depth modeling
- 47. BWA-Meth acceleration
- 48. MethylDackel follow-up extraction
- 50. CRISPR-detector whole-genome editing evaluation

For this stage, these should return a boundary answer rather than a synthesized deep-dive explanation.

### C. Not appropriate for deterministic first-line support in the current product

These are mostly benchmark, competitive, cost, marketing, future-looking, or exact quantitative claims:

- 8. Azure / AWS cloud cost down to `1~5` USD
- 9. BWA-turbo `4x` speed / low-quality read comparison
- 18. WES using WGS model impact on total errors
- 22. `100 万` sample joint-calling scalability claim
- 27. UMI + TNscope vs `fgbio + Vardict` at `0.1%-0.3%`
- 31. ONT homopolymer handling vs `Clair3`
- 35. `CYP21A2` case-study style performance claim
- 36. exact PacBio depth threshold that beats another setup
- 39. pangenome SV `94.77%` style precision claim
- 40. pangenome `60 分钟以内` / saved compute relative to graph assembly
- 41. current and future HPRC graph sample-count roadmap
- 46. `hap-eval` vs `Truvari` superiority claim

These should not be treated as normal support lookups. They require benchmark evidence, release-note verification, papers, or up-to-date product collateral.

## Product Implication

The first-stage material is enough to improve the current system if the goal is:

- route more accurately
- answer supported support questions more consistently
- refuse unsupported deep-dive questions safely
- turn adversarial prompts into regression coverage

The first-stage material is not enough if the goal is:

- confidently answering benchmark claims
- quoting exact performance numbers
- doing competitive positioning
- answering future roadmap questions

## Implementation Shape

### 1. Add a deterministic reference-boundary path

When a prompt is a deep mechanism / benchmark / comparison / roadmap question without structured support coverage, return a stable `【资料边界】` answer instead of model synthesis.

### 2. Convert the 50 prompts into executable adversarial data

Store each prompt with:

- question id
- expected mode: `supported`, `boundary`, or `clarify`
- audit reason

Use the data file for both human audit and automated drill.

### 3. Expand the drill to independent subprocess execution

The drill should run the CLI in a fresh subprocess per case so route state and chat state do not leak between prompts.

### 4. Lock the behavior with tests

The core regression is not “answer every question”. The regression is:

- never fall back to the old MVP message
- never hallucinate benchmark/comparison claims from sparse snippets
- keep supported lookup behavior intact

## Acceptance Criteria

- All 50 NotebookLM prompts are classified in a committed audit artifact.
- Unsupported deep-dive prompts return `【资料边界】` instead of free-form model fallback.
- Existing supported reference answers still pass.
- The adversarial drill runs the expanded corpus through fresh subprocesses and passes.
