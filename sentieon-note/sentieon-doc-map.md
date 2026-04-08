# Sentieon Documentation Map

主源:

- 官方文档站: <https://support.sentieon.com/docs/>
- 本地 PDF: `Sentieon202503.03.pdf`
- 官方 GitHub 组织: <https://github.com/Sentieon>
- 中文资料站: <https://doc.insvast.com/p/sentieon/>

## 1. 文档整体结构

从本地 PDF 提取到的主目录可以分成几块:

1. Quick Start
2. 各类典型 pipeline 用法
3. `sentieon-cli` 单命令流水线
4. UMI / dedup / somatic 专题
5. application notes
6. 底层二进制与算法手册
7. troubleshooting
8. release notes

## 2. 主要章节

### Quick Start

- `1 Sentieon Quick Start`
- 覆盖最基础的环境要求、安装包解压、许可证环境变量、首次 DNAscope 运行

关键点:

- Linux 环境
- 小 panel / WES 建议至少 16 GB 内存
- WGS 建议至少 64 GB 内存
- 文档建议使用高速 SSD
- `SENTIEON_PYTHON`
- `SENTIEON_LICENSE`
- `SENTIEON_INSTALL_DIR`
- `SENTIEON_TMPDIR`

### 典型流程

- `2 Typical usage for Pangenome`
- `3 Typical usage for DNAseq`
- `4 Typical usage for DNAscope`
- `5 Typical usage for TNseq`
- `6 Typical usage for TNscope`
- `7 Typical usage for RNA variant calling`

适用场景:

- `DNAseq`: 常规 germline 流程
- `DNAscope`: diploid organism 的短读长 germline 流程
- `TNseq` / `TNscope`: somatic
- `RNA variant calling`: RNA 变异调用
- `Pangenome`: graph / pangenome 参考框架

### sentieon-cli

- `9.1 DNAscope`
- `9.2 DNAscope LongRead`
- `9.3 DNAscope Hybrid`
- `9.4 Sentieon Pangenome`

这部分把传统多步流程包装成单命令，可用于查看 CLI 入口、参数和输出。

### 专题和 app notes

- `10 Deduplication and UMI Handling`
- `11 Somatic Variant Calling for SNPs and Indels`
- `12 Sentieon Application Notes`

其中比较实用的 app notes:

- `12.1 Arguments Correspondence`
- `12.4 Germline Copy Number Variant Calling for Whole-Genome-Sequencing with CNVscope`
- `12.5 Distributed Mode`
- `12.8 Using jemalloc to Optimize Memory Allocation`
- `12.10 Description of output files and fields`
- `12.11 Recommendations on Read Groups`

### 底层工具手册

- `13 Introduction`
- `14 DRIVER binary`
- `15 BWA binary`
- `16 minimap2 binary`
- `17 STAR binary`
- `18 UTIL binary`
- `19 UMI binary`
- `20 PLOT script`
- `21 LICSRVR binary`
- `22 LICCLNT binary`

如果需要回答精细参数、兼容 GATK 风格、或者解释 `driver --algo` 工作方式，这部分可作为主参考。

### 排障和版本变化

- `23 Troubleshooting`
- `24 Release notes and usage changes`

## 3. 产品 / 流程定位速览

### Germline

- `DNAscope`: 短读长 germline variant calling，适合 diploid organism
- `DNAseq`: 短读长 germline 流程；手册写到当 DNAscope 的 diploid recommendation 不适用时可使用它
- `DNAscope LongRead`: PacBio HiFi / ONT 长读长 germline
- `DNAscope Hybrid`: 同一样本短读长 + 长读长联合调用
- `Pangenome`: 使用 pangenome graph 的短读长流程

### Somatic

- `TNseq`, `TNscope`, `TNhaplotyper`, `TNhaplotyper2 + TNfilter`

### RNA

- `RNASplitReadsAtJunction`
- `Haplotyper`

### 支撑工具

- `Dedup`, `LocusCollector`, `QualCal`, `GVCFtyper`, `VarCal`, `ApplyVarCal`
- `BWA`, `minimap2`, `STAR`
- `UTIL`, `UMI`, `LICSRVR`, `LICCLNT`

## 4. sentieon-cli 单命令流水线要点

### `sentieon-cli dnascope`

输入类型:

- 短读长 DNA
- 输入可以是 `FASTQ`、`uBAM/uCRAM`、已对齐 `BAM/CRAM`

核心参数:

- `-r REFERENCE`
- `--r1_fastq` / `--r2_fastq`
- `--readgroups`
- `-m MODEL_BUNDLE`
- `-d DBSNP`
- `-b BED`
- `-t THREADS`
- `--pcr_free`
- `-g` 输出 gVCF
- `--duplicate_marking markdup|rmdup|none`
- `--assay WGS|WES`
- `--consensus`

输出重点:

- `sample.vcf.gz`
- `sample_deduped.cram` 或 `.bam`
- `sample_svs.vcf.gz`
- `sample_metrics/`
- `sample_metrics/multiqc_report.html`

### `sentieon-cli dnascope-longread`

输入类型:

- PacBio HiFi
- Oxford Nanopore

新增关键参数:

- `--tech HiFi|ONT`
- `--haploid_bed`
- `--cnv_excluded_regions`

依赖更重:

- `python >= 3.8`
- `bcftools`
- `bedtools`
- `samtools`
- `mosdepth`
- `hificnv`

### `sentieon-cli dnascope-hybrid`

输入类型:

- 同一样本同时有短读长和长读长
- 目标是联合提升 SNV / indel / SV / CNV 结果

输入模式:

- 对齐后的短读长 + 长读长
- 或未对齐短读长 FASTQ + 未对齐长读长 uBAM/uCRAM

输出重点:

- `sample.vcf.gz`
- `sample.sv.vcf.gz`
- `sample.cnv.vcf.gz`
- 对齐后的短读长 / 长读长文件
- `sample_metrics/`

### `sentieon-cli pangenome`

使用限制:

- 需要 graph/pangenome 表示来增强复杂区域调用

限制:

- 文档明确写到当前只支持 `GRCh38`
- 且要求 `UCSC-style contig names`，即 `chr1`, `chr2` 这种命名

## 5. 传统 driver/algo 体系

适合:

- 自定义脚本
- GATK 风格迁移
- 分布式分片
- 更细粒度调参

高频组件:

- `driver --algo LocusCollector`
- `driver --algo Dedup`
- `driver --algo Haplotyper`
- `driver --algo DNAscope`
- `driver --algo GVCFtyper`
- `driver --algo VarCal`
- `driver --algo ApplyVarCal`

文档里还提供了:

- 参数对应关系
- 输出字段说明
- read group 建议
- 分布式运行样例

## 6. 排障重点

### 参考与输入格式

- 参考 FASTA 需要配套 `.fai`
- BWA 对齐还需要 BWA index
- 文档不支持普通 gzip 压缩的 VCF 作为可索引输入，要求 `bgzip`
- 不支持 gzipped FASTA

### Read Group

- RG 信息很关键
- 如果 tumor / normal BAM 里 `RGID` 相同，会出问题
- 文档给了用 `samtools addreplacerg` 和 `samtools reheader` 修改的办法

### BWA 内存

- 从已排序 BAM 反转出的 FASTQ 可能把 unmapped reads 堆到末尾，导致 BWA 异常吃内存
- `BWA fails with error: Killed` 常常对应 OOM
- 可以从内核日志确认，并调小 BWA 内存参数

### QualCal 表不匹配

- `none of the QualCal tables is applicable to the input BAM files`
- 说明 recalibration table 和输入 BAM 对不上，或者 RG 头信息不对

## 7. 分布式与大 cohort

`12.5 Distributed Mode` 可用于回答:

- 多机分发 BWA
- shard 化 germline pipeline
- 大规模 joint calling
- 云环境对象存储上的 GVCF 分片下载

关键点:

- 合并 partial results 时顺序必须严格正确
- GVCF 输入顺序在每个 shard 间必须一致
- 大 cohort joint calling 可关注 `GVCFtyper --genotype_model multinomial`
- 文档给出的 shard size 示例约为 `100M bases`
- I/O 往往是瓶颈，文档对大规模 joint calling 提到存储吞吐建议约 `600 MBps`

## 8. 近期版本变化摘录

从 release notes 中摘录的更新包括:

- `202503`: 新增 hybrid short + long-read variant calling
- `202503`: 新增 CRAM 3.1 读写支持
- `202503`: `GVCFtyper` 支持 long-read DNAscope gVCF 联合调用
- `202308.03`: ARM CPU 支持 STAR 和 minimap2
- `202308.03`: 增加 `SimplifyCigarTransform`
- `202308.02`: `Dedup` 增加 consensus / UMI-aware metrics
- `202112.06`: `LongReadSV` 支持 ONT
- 更早版本还记录了 ONT、小变异调用、分布式能力和错误检查相关更新

## 9. 资料使用顺序

如果要在本地资料里继续展开，可按这个顺序查:

1. 本地 PDF 关键词搜索
2. `sentieon-doc-map.md`
3. `sentieon-github-map.md`
4. `thread-019d5249-summary.md`
5. 在线文档原页

补充判断:

- 需要“官方说明、参数含义、章节原文”时，看文档站 / PDF
- 需要“实际脚本、模型列表、安装入口、容器样例、云部署样板”时，看官方 GitHub
- 需要“中文说明、平台化流程概览、对内沟通材料”时，可参考中文资料站，但技术细节以官方源为准
