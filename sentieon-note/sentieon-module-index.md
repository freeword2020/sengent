# Sentieon Module Index

主文件:

- 结构化索引: `sentieon-modules.json`
- 当前索引版本: `202503.03`

这份文件是给人读的总表；程序优先读取 `sentieon-modules.json`。

## 1. Alignment

- `Alignment`: 比对模块总览，覆盖 `BWA`、`STAR`、`Minimap2`
- `Sentieon BWA`: 短读长 DNA 比对
- `Sentieon STAR`: RNA 比对
- `Sentieon Minimap2`: 长读长比对

## 2. Germline Variant Calling

- `DNAseq`: 传统短读长胚系流程，非 diploid 场景优先考虑
- `DNAscope`: 短读长主力胚系流程，推荐 diploid organism
- `DNAscope LongRead`: 长读长胚系流程，支持 HiFi / ONT
- `DNAscope Hybrid`: 短读长 + 长读长联合调用
- `Sentieon Pangenome`: graph/pangenome 参考框架下的短读长流程
- `Genotyper`: 非 haplotype-based 胚系 caller
- `Haplotyper`: haplotype-based 胚系 caller
- `GVCFtyper`: joint call / joint genotyping 核心算法
- `Joint Call`: 多样本联合分型流程概念入口
- `CNVscope`: 胚系 CNV 模块

## 3. Somatic Variant Calling

- `TNseq`: 体细胞流程家族总称
- `TNscope`: 主力体细胞 caller
- `TNsnv`: 体细胞 SNV caller
- `TNhaplotyper`: 体细胞 haplotype-based caller
- `TNhaplotyper2`: 升级版体细胞 haplotype-based caller

## 4. RNA and Specialized Analysis

- `RNAseq`: RNA 变异调用流程
- `GeneEditEvaluator`: 基因编辑序列分析模块

## 5. BAM / Preprocess / Filtering

- `Dedup`: duplicate marking / consensus / UMI-aware dedup
- `LocusCollector`: Dedup 上游打分统计
- `QualCal`: base quality recalibration
- `ReadWriter`: 读段处理辅助模块
- `Realigner`: 传统局部重比对模块
- `VarCal`: VQSR 建模
- `ApplyVarCal`: 应用 VQSR 模型
- `UMI`: UMI 提取与处理

## 6. QC / Architecture / Support

- `QC`: QC 模块总览，覆盖 alignment、coverage、quality、artifact、contamination 等 metrics
- `Distributed Mode`: 分布式 / shard 运行方法
- `Python API`: 二次开发与平台封装入口
- `BCL-FASTQ Tool`: FASTQ 生成模块

## 7. 索引用法

优先适合回答:

- `DNAscope 是什么`
- `DNAscope 支持什么输入`
- `GVCFtyper 是不是 joint call`
- `TNscope 和 TNseq 什么关系`
- `CNVscope 主要做什么`
- `sentieon-cli dnascope 的 --pcr_free 是什么`
- `GVCFtyper 的 --genotype_model multinomial 是什么`

当前已覆盖的参数级索引:

- `DNAscope`: `--pcr_free`, `--duplicate_marking`, `--assay`, `--consensus`
- `DNAscope LongRead`: `--tech`, `--haploid_bed`, `--cnv_excluded_regions`
- `DNAscope Hybrid`: `--sr_duplicate_marking`, `--lr_align_input`, `--lr_input_ref`
- `Joint Call`: `--genotype_model`, `--split_by_sample`
- `GVCFtyper`: `--genotype_model`, `--split_by_sample`
- `TNscope`: `--trim_soft_clip`, `--disable_detector`

当前不直接覆盖:

- 全量参数级索引
- 每个模块的完整命令模板
- 每个模块的所有 edge case

如果问题已经进入参数细节，例如:

- `sentieon-cli dnascope 的 --pcr_free 是什么`

则程序会先命中结构化参数索引，再附带 manual / notes / GitHub 的 source context。

如果参数还没有进入当前索引覆盖面，则回退到原始资料片段检索。
