# Sentieon Script Index

当前脚本索引和脚本状态回答覆盖 10 类问句:

- `RNAseq` 参考脚本
- `DNAseq` 参考脚本
- `DNAscope` 参考命令
- `DNAscope LongRead` 参考命令
- `DNAscope Hybrid` 参考命令
- `Sentieon Pangenome` 参考命令
- `CNVscope` 参考脚本
- `TNscope` 参考脚本
- `Joint Call` 参考命令
- `GeneEditEvaluator` 参考脚本状态说明

整理原则:

- 命令骨架来自官方 manual / PDF 的 step-by-step usage 或 `sentieon-cli` 章节
- GitHub 主要用来补“这类脚本/单命令入口在哪个仓库看”
- 不把长脚本整段硬塞进回答，先给稳定骨架，再提示去哪里追完整实现

当前覆盖:

- `RNAseq`
  - manual `7 Typical usage for RNA variant calling`
  - 骨架包含 `STAR -> LocusCollector/Dedup -> RNASplitReadsAtJunction -> Haplotyper/DNAscope`
- `DNAseq`
  - manual `3 Typical usage for DNAseq`
  - 骨架包含 `BWA -> LocusCollector/Dedup -> QualCal -> Haplotyper`
- `DNAscope`
  - manual `9.1 DNAscope`
  - 对应 `sentieon-cli dnascope` 单命令骨架
- `DNAscope LongRead`
  - manual `9.2 DNAscope LongRead`
  - 对应 `sentieon-cli dnascope-longread` 单命令骨架，以及 `--tech` / `--haploid_bed` / `--cnv_excluded_regions`
- `DNAscope Hybrid`
  - manual `9.3 DNAscope Hybrid`
  - 对应 `sentieon-cli dnascope-hybrid` 的 aligned-input 骨架，并提示未对齐 short+long read 的切换入口
- `Sentieon Pangenome`
  - manual `2 Typical usage for Pangenome` 和 `9.4 Sentieon Pangenome`
  - 对应 `sentieon-cli sentieon-pangenome` 单命令骨架，以及 `--hapl` / `--gbz` / `--pop_vcf`
- `CNVscope`
  - manual `12.4 Germline Copy Number Variant Calling for Whole-Genome-Sequencing with CNVscope`
  - 对应 `CNVscope -> CNVModelApply` 两步骨架，以及 male sample 需要 autosomes / haploid 区域分开跑
- `TNscope`
  - manual `6 Typical usage for TNscope`
  - 对应 tumor-normal 体细胞调用骨架
- `Joint Call`
  - manual `8.2` 和 `14.2.20 GVCFtyper`
  - 对应 `sentieon driver --algo GVCFtyper` 联合分型骨架
- `GeneEditEvaluator`
  - 当前本地官方资料只有 release notes 级提及
  - 程序会稳定回答“未提供可确定性复用的参考脚本或 CLI 骨架”，而不是回退到模型硬编命令

当前不直接覆盖:

- 多轮跟进里的省略问句
  - 例如上一轮问了 `RNAseq`，下一轮只说 `示例脚本也可以`
- `sentieon-scripts` 仓库里的长 shell 脚本全文整理
- `GeneEditEvaluator` 的真实脚本骨架
  - 当前本地官方资料只有 release note 级提及，还没有足够稳定的 usage/CLI 片段可索引

资料入口:

- `sentieon-cli` 风格命令骨架
- manual 的 step-by-step usage
- `sentieon-github-map.md` 里的 `sentieon-scripts` 和 `sentieon-cli`
