# Sentieon Summary For Thread 019d5249-f1d6-75c0-8d3c-99e3e97e9835

这份文件是线程级速查摘录，内容来自本地官方 PDF、官方 GitHub 整理和少量本地派生索引。

使用边界:

- 需要确定性回答时，以 `Sentieon202503.03.pdf`、官方文档站和官方 GitHub 为准
- 这份文件只保留事实摘录和资料入口，不提供流程推荐模板

## 1. 版本与资料层级

- 官方文档站: <https://support.sentieon.com/docs/>
- 官方 GitHub 组织: <https://github.com/Sentieon>
- 中文资料站: <https://doc.insvast.com/p/sentieon/>
- 本地 PDF 文件名: `Sentieon202503.03.pdf`
- PDF 首页正文显示: `Release 202503.03`
- PDF 日期: `Mar 30, 2026`

资料层级:

- 一线资料: 官方文档站 / 本地 PDF / 官方 GitHub
- 二线资料: 中文资料站
- 派生资料: 本目录里的 `sentieon-modules.json`、`sentieon-doc-map.md`、`sentieon-github-map.md`

## 2. 官方 PDF 中可直接定位的主要流程

- `2 Typical usage for Pangenome`
- `3 Typical usage for DNAseq`
- `4 Typical usage for DNAscope`
- `5 Typical usage for TNseq`
- `6 Typical usage for TNscope`
- `7 Typical usage for RNA variant calling`
- `9.1 DNAscope`
- `9.2 DNAscope LongRead`
- `9.3 DNAscope Hybrid`
- `9.4 Sentieon Pangenome`
- `12.4 Germline Copy Number Variant Calling for Whole-Genome-Sequencing with CNVscope`
- `12.5 Distributed Mode`

## 3. 直接可引用的流程限制和说明

- PDF 写明: `DNAscope is only recommended for use with samples from diploid organisms. For other samples, please use DNAseq.`
- PDF 写明: `DNAscope Hybrid` 是使用单一样本 short-read 和 long-read 数据的 germline variant calling pipeline
- PDF 写明: `Sentieon Pangenome` 当前只支持 `Minigraph-Cactus` 的 `GRCh38` pangenome，并要求 `UCSC-style contig names`
- PDF 写明: `CNVscope` 与 `CNVModelApply` 必须使用同一 model
- PDF 写明: human male sample 的 `CNVscope` 调用需要区分 diploid 与 haploid 区域分别运行
- PDF 写明: large joint calls with more than `1000` samples 可使用 `--genotype_model multinomial`
- PDF 写明: `--split_by_sample` 是 `GVCFtyper merge` 阶段的选项

## 4. 环境与许可证摘录

- Quick Start 写明 Linux 环境
- PDF 写明软件至少需要 `16 GB` 内存，并建议使用 `64 GB` 内存
- PDF 写明可设置:
  - `SENTIEON_PYTHON`
  - `SENTIEON_LICENSE`
  - `SENTIEON_INSTALL_DIR`
  - `SENTIEON_TMPDIR`
- 许可证相关工具:
  - `LICSRVR`
  - `LICCLNT`

常见检查命令:

```bash
sentieon licclnt ping -s <host>:<port>
sentieon licclnt query -s <host>:<port> klib
```

## 5. 输入格式和排障摘录

- 参考 FASTA 需要 `.fai`
- BWA 场景需要 BWA index
- PDF 写明普通 gzip VCF 不适合作为随机访问输入，应使用 `bgzip`
- PDF 写明不支持 gzipped FASTA
- PDF 写明 FASTQ 需要 SANGER quality format
- troubleshooting 章节包含:
  - `BWA fails with error: Killed`
  - `none of the QualCal tables is applicable`

## 6. 官方 GitHub 仓库入口

- `sentieon-cli`: 单命令 pipeline CLI
- `sentieon-models`: model bundle 清单
- `sentieon-scripts`: 辅助脚本仓库
- `sentieon-docker`: Dockerfile 样例
- `terraform`: license server 云部署样板
- `segdup-caller`: segmental duplication 区域相关 caller

## 7. 本地索引当前覆盖

- 模块介绍 / 输入 / 输出 / 相关模块
- `DNAscope` 高频参数
- `DNAscope LongRead` 高频参数
- `DNAscope Hybrid` 高频参数
- `Sentieon Pangenome` 高频参数
- `CNVscope` 高频参数
- `Joint Call` / `GVCFtyper` 高频参数
- `TNscope` 高频参数
- `RNAseq`、`DNAseq`、`DNAscope`、`DNAscope LongRead`、`DNAscope Hybrid`、`Sentieon Pangenome`、`CNVscope`、`TNscope`、`Joint Call` 的参考命令骨架

## 8. 当前刻意不做确定性承诺的条目

- `GeneEditEvaluator`: 本地官方 PDF 只有 release notes 提及，未见稳定 usage/CLI 章节
- `Python API`: 当前本地官方 PDF 未见详细章节
- `BCL-FASTQ Tool`: 当前本地官方 PDF 未见详细章节
