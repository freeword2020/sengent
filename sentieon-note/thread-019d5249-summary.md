# Sentieon Summary For Thread 019d5249-f1d6-75c0-8d3c-99e3e97e9835

这份是给当前线程直接复用的精简背景，不追求覆盖全部章节，优先保留高频判断点、命令骨架、限制和排障信息。

## 1. 先记住版本

- 官方站点来源: <https://support.sentieon.com/docs/>
- 官方 GitHub 组织: <https://github.com/Sentieon>
- 中文资料站: <https://doc.insvast.com/p/sentieon/>
- 本地 PDF 文件名: `Sentieon202503.03.pdf`
- PDF 首页正文显示: `Release 202503.03`
- PDF 日期: `Mar 30, 2026`

如果在线文档和本地 PDF 出现细节不一致，优先注明具体版本号，避免在线程里混淆不同 release。

GitHub 侧的更新时间也值得带上:

- `sentieon-cli` 组织页显示更新于 `Apr 1, 2026`
- `sentieon-models` 更新于 `Mar 10, 2026`
- `sentieon-scripts` 更新于 `Jan 27, 2026`

中文资料站可作为二线参考，适合:

- 用中文快速理解模块和流程
- 按平台查看 DNAscope 流程拆分
- 查中文教程和应用案例

但如果出现参数、版本、限制上的冲突:

- 以官方文档站 / PDF / 官方 GitHub 为准

## 2. 流程选择

### 短读长 germline

首选:

- `DNAscope`

但有一个明确限制:

- 文档注明 `DNAscope` 只推荐用于 `diploid organisms`
- 非 diploid 样本更适合 `DNAseq`

### 长读长 germline

首选:

- `DNAscope LongRead`

支持:

- `PacBio HiFi`
- `Oxford Nanopore`

### 短读长 + 长读长联合

首选:

- `DNAscope Hybrid`

适合:

- 同一样本既有 short-read 又有 long-read
- 需要同时产出小变异、SV、CNV

### graph / pangenome

首选:

- `Sentieon Pangenome`

当前限制:

- 仅支持 `GRCh38`
- 要求 `chr1` 这种 `UCSC-style contig names`

### somatic

- `TNseq`
- `TNscope`

## 3. 环境和许可证

### 基础环境

- Linux
- 小 panel / WES 至少约 `16 GB RAM`
- WGS 至少约 `64 GB RAM`
- 推荐本地 SSD

### 常见环境变量

```bash
export SENTIEON_PYTHON=/path/to/python
export SENTIEON_LICENSE=/path/to/license.lic
export SENTIEON_LICENSE=host:port
export SENTIEON_INSTALL_DIR=/path/to/sentieon/bin
export SENTIEON_TMPDIR=/fast/local/tmp
```

### 许可证相关工具

- `LICSRVR`: license server
- `LICCLNT`: license client

常见检查:

```bash
sentieon licclnt ping -s <host>:<port>
sentieon licclnt query -s <host>:<port> klib
```

## 4. `sentieon-cli` 是最省事的入口

如果线程需要给出“最短可运行方案”，优先回答 `sentieon-cli`。

### DNAscope

典型骨架:

```bash
sentieon-cli dnascope \
  -r ref.fa \
  --r1_fastq sample_R1.fastq.gz \
  --r2_fastq sample_R2.fastq.gz \
  --readgroups "@RG\tID:foo\tSM:bar\tLB:lib1\tPL:ILLUMINA" \
  -m model_bundle \
  -d dbsnp.vcf.gz \
  -b regions.bed \
  -t 32 \
  sample.vcf.gz
```

核心输出:

- `sample.vcf.gz`
- `sample_deduped.cram` 或 `.bam`
- `sample_svs.vcf.gz`
- `sample_metrics/`
- `sample_metrics/multiqc_report.html`

常用可选项:

- `-g`: 同时输出 gVCF
- `--pcr_free`
- `--duplicate_marking markdup|rmdup|none`
- `--assay WGS|WES`
- `--consensus`
- `--dry_run`

### DNAscope LongRead

典型新增参数:

- `--tech HiFi|ONT`
- `--haploid_bed`
- `--cnv_excluded_regions`

### DNAscope Hybrid

它会组合:

- short-read
- long-read
- 小变异
- SV
- CNV

这是 `202503` 版本里最值得注意的新能力之一。

如果线程里需要真实安装入口或源码位置，GitHub 上对应仓库是:

- `sentieon-cli`
- `sentieon-models`

## 5. 传统多步流程还很重要

如果线程是在解释老脚本、兼容 GATK 风格命令、或者讨论精细调参，应该回到 `driver --algo`。

高频组件:

- `LocusCollector`
- `Dedup`
- `DNAscope`
- `Haplotyper`
- `GVCFtyper`
- `VarCal`
- `ApplyVarCal`

一个安全的表达方式是:

- `sentieon-cli` 适合单样本和标准流程
- `driver --algo` 适合高级用户、自定义拼装、分布式执行和老 pipeline 迁移

## 6. Read Group 是高频坑点

文档里多次强调 RG 信息。

线程里如果遇到下列问题，要优先怀疑 RG:

- tumor / normal 输入混乱
- `QualCal` 表不适配
- 多文件合并后 sample 识别异常
- hybrid pipeline 报输入 `RG-SM tag` 不一致

可复用结论:

- `RG ID` 需要唯一
- `SM` 要一致地代表同一样本
- 如果输入文件 `RGID` 冲突，可用 `samtools addreplacerg` 和 `samtools reheader` 修

## 7. 参考文件和输入格式限制

- 参考 FASTA 需要 `.fai`
- BWA 场景需要 BWA index
- 若参考带 alternate contigs，短读长对齐最好同时提供 `.alt`
- 不支持普通 gzip VCF 作为索引随机访问输入，应该用 `bgzip`
- 不支持 gzipped FASTA
- FASTQ 需要 SANGER quality format

## 8. 常见排障口径

### `BWA fails with error: Killed`

高概率是:

- 系统 OOM，进程被 SIGKILL

建议口径:

- 先查内核日志确认 OOM
- 再考虑降低 BWA 内存占用

### `none of the QualCal tables is applicable`

常见原因:

- recal table 和 BAM 不匹配
- BAM header / RG 信息错误

### 从排序 BAM 反转出来的 FASTQ 导致 BWA 吃内存

文档解释:

- unmapped reads 可能被堆到 FASTQ 末尾
- BWA 在尾部会异常耗内存

建议:

- 先按 read name 重新整理，再导出 FASTQ

## 9. 大规模联合分型和分布式

这一块对线程非常有用，因为很多问题最后都落到“能不能扩到大 cohort / 云上怎么跑”。

关键点:

- `12.5 Distributed Mode` 是主章节
- 合并 shard 结果时输入顺序必须严格一致
- `GVCFtyper` 在大 cohort 时可考虑 `--genotype_model multinomial`
- 大规模 joint calling 常常是 I/O 限制，不只是 CPU 限制
- 文档建议大规模场景可考虑 `100M bases` 左右 shard
- 对极大 cohort 还要考虑 `ulimit -n`、`ulimit -s`、`jemalloc`、`VCFCACHE_BLOCKSIZE`

对外回答时可直接说:

- Sentieon 支持 shard-based distributed joint calling
- 但 sample order 和 shard merge order 都必须严格稳定

## 10. 最近版本变化里最有用的几条

从 release notes 抽出的高价值更新:

- `Release 202503`: 新增 hybrid short + long-read variant calling
- `Release 202503`: 新增 CRAM 3.1 读写支持
- `Release 202503`: `GVCFtyper` 支持 long-read DNAscope gVCF 联合调用
- `Release 202308.03`: ARM CPU 支持 STAR 和 minimap2
- `Release 202308.03`: `Dedup` 新增 consensus / UMI-aware metrics
- `Release 202112.06`: `LongReadSV` 支持 ONT

## 11. GitHub 该怎么用

优先这样分工:

- 查参数、限制、官方解释: 文档站 / PDF
- 查可执行脚本、安装方式、模型 bundle 清单: GitHub
- 查中文概览、教程化表达、平台化中文流程说明: 中文资料站

核心仓库:

- `sentieon-cli`: 官方单命令 pipeline 入口
- `sentieon-models`: 各平台 model bundle 清单和 YAML 索引
- `sentieon-scripts`: 示例 pipeline、内存估算、MNP merge、TNscope filter 等辅助脚本
- `sentieon-docker`: 官方 Dockerfile 样例
- `terraform`: AWS / Azure license server 部署样板
- `segdup-caller`: segmental duplication 区域难基因调用

## 12. 中文资料站怎么用

这个站点的目录结构比较适合作为培训和二线支持材料，当前我看到的高价值内容包括:

- `Sentieon 中文手册`
- `Sentieon软件快速入门指南`
- `Sentieon 软件模块总述`
- 按平台拆开的 `DNAscope` 流程:
  - Illumina
  - Complete Genomics
  - PacBio LongRead
  - Ultima
  - Element Bio
  - Nanopore LongRead
- `Sentieon 软件应用教程`
- `泛基因组分析流程详解`
- 动植物 WGS 流程
- `Sentieon文献解读`

对线程最有用的定位:

- 作为中文说明参考
- 作为“按平台找对应流程”的快速导航
- 作为对外或对内中文口径的补充材料

不建议单独依赖它来回答:

- 精细参数默认值
- 最新 release 级别的版本变化
- 严格的兼容性和限制判断

## 13. 回答线程时的推荐表达模板

### 问“该用哪个流程”

- 短读长 diploid germline 用 `DNAscope`
- 非 diploid germline 更偏向 `DNAseq`
- 长读长用 `DNAscope LongRead`
- 短读长加长读长联合用 `DNAscope Hybrid`
- somatic 用 `TNscope` / `TNseq`

### 问“最短命令怎么写”

- 优先给 `sentieon-cli`
- 再补一行说明需要 `reference + index + model bundle + dbSNP + read groups`

### 问“为什么报错”

优先排查:

1. 许可证
2. reference / index 是否齐全
3. RG 是否正确
4. 输入压缩格式是不是官方支持的那种
5. 内存和 I/O
