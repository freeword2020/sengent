# Sentieon Module Index Design

## Goal

为 `sentieon-assist` 增加一层稳定可控的模块索引，让“模块介绍”和“常见能力/输入输出/相关模块”类问题优先命中结构化索引，而不是完全依赖全文关键词检索。

## Why

当前 reference 问答已经能用本地资料做证据检索，但仍有两个问题：

- 对 `dnascope是什么` 这类中英混写、无空格问法，全文检索召回不够稳定
- 即使命中资料，也可能先拿到 PDF 目录、`References`、流程摘要等噪声片段，而不是模块定义段

用户已经确认，希望第一版优先实现：

- `JSON + Markdown`
- 稳定可控
- 主模块全部纳入显式索引

## Scope

第一版覆盖：

- alignment: `BWA`, `STAR`, `Minimap2`
- germline: `DNAseq`, `DNAscope`, `DNAscope LongRead`, `DNAscope Hybrid`, `Genotyper`, `Haplotyper`, `GVCFtyper`
- somatic: `TNseq`, `TNscope`, `TNsnv`, `TNhaplotyper`, `TNhaplotyper2`
- CNV / graph / joint: `CNVscope`, `Pangenome`, `Joint Call`
- support/tooling: `QC`, `RNAseq`, `GeneEdit`, `Dedup`, `LocusCollector`, `QualCal`, `VarCal`, `ApplyVarCal`, `UMI`, `ReadWriter`, `Distributed Mode`, `Python API`, `BCL-FASTQ`, `Realigner`

第一版不做：

- embedding / vector store
- 全量参数级索引
- 自动从 PDF 抽取并生成索引

## Data Shape

索引文件：

- `sentieon-note/sentieon-modules.json`
- `sentieon-note/sentieon-module-index.md`

`JSON` 的每个模块条目使用统一字段：

- `id`
- `name`
- `aliases`
- `category`
- `summary`
- `scope`
- `inputs`
- `outputs`
- `common_questions`
- `related_modules`
- `source_priority_notes`
- `sources`

## Runtime Behavior

reference 查询路径增加模块索引优先逻辑：

1. 先从 query 中匹配模块索引
2. 如果是“是什么 / 做什么 / 支持什么输入 / 输出有哪些 / 相关模块”这类问题，直接返回确定性答案
3. 如果是参数问题，例如带 `--pcr_free`，则把模块索引转成高优先级 evidence，再补充原有 source search 结果，让模型组织答案
4. 如果没有命中模块索引，再退回现有全文检索路径

## Main Benefit

这次改动的核心收益不是“更多资料”，而是“先命中结构化定义，再补原文证据”。这样可以明显降低：

- 目录页片段抢占第一证据
- 泛词噪声命中
- 大模块定义回答不稳定

## Files

- New: `src/sentieon_assist/module_index.py`
- Modify: `src/sentieon_assist/answering.py`
- Modify: `src/sentieon_assist/classifier.py`
- Modify: `src/sentieon_assist/sources.py`
- New: `sentieon-note/sentieon-modules.json`
- New: `sentieon-note/sentieon-module-index.md`
- Modify: `tests/test_answering.py`
- Modify: `tests/test_classifier.py`
- Modify: `tests/test_sources.py`
- Update: `README.md`
- Update: `docs/project-context.md`

