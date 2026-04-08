# External Tool Reference

整理日期: `2026-04-08`

使用边界:

- 这份笔记只整理外部官方工具文档，用于解释工具定位、常见输出和高频命令入口。
- 不把这些工具文档写成 Sentieon 官方建议；涉及 Sentieon 流程时，仍以 Sentieon manual / app note 为准。
- 这里的“关联排查”只表示常见排错方向，不代替具体现场复现。

## 1. samtools

主源:

- <https://www.htslib.org/doc/samtools.html>

提炼:

- `samtools` 是面向 `SAM/BAM/CRAM` 的通用工具集合。
- 高频子命令里，`view`、`sort`、`index`、`quickcheck`、`reheader`、`addreplacerg`、`faidx`、`idxstats` 对排错很常见。
- 当问题和“文件是否完整、是否已排序、header 是否可读、RG 是否需要修补”相关时，通常都值得先看 `samtools` 层。

## 2. bcftools

主源:

- <https://www.htslib.org/doc/bcftools.html>

提炼:

- `bcftools` 主要处理 `VCF/BCF` 的查看、过滤、统计、规范化和索引。
- 高频子命令里，`view`、`query`、`stats`、`norm`、`index` 最常见。
- 当问题和“VCF/BCF 是否可读、是否已压缩索引、header/contig/sample 是否一致”相关时，通常先从 `bcftools` 层定位。

## 3. FastQC

主源:

- <https://www.bioinformatics.babraham.ac.uk/projects/fastqc/>

提炼:

- `FastQC` 是原始测序数据质量控制工具，官方页面明确支持从 `BAM`、`SAM` 或 `FastQ` 导入数据。
- 它的定位是生成质量控制报告，而不是做 trimming、比对或变异调用。
- 当问题是“原始 reads 质量、GC、重复度、接头污染、每碱基质量分布怎么看”时，可先回到 `FastQC` 报告层。

## 4. MultiQC

主源:

- <https://docs.seqera.io/multiqc>

提炼:

- `MultiQC` 的定位是汇总其他工具结果，不自己重新做上游分析。
- 官方文档强调它会把多个日志和报告整合成一个汇总视图，常见产物是单个 HTML 报告和解析后的数据目录。
- 当问题是“多个 QC 工具结果怎么集中看、某个样本是不是整体异常”时，`MultiQC` 适合作为聚合入口，但不是原始证据来源本身。

## 5. bgzip / tabix

主源:

- `bgzip` manual: <https://www.htslib.org/doc/bgzip.html>
- `tabix` manual: <https://www.htslib.org/doc/tabix.html>

提炼:

- `bgzip` 是适合随机访问压缩文本格式的块压缩工具；很多需要区间访问的 `VCF/BED/GFF` 类文件会要求这种压缩方式。
- `tabix` 用于给坐标排序后的通用文本格式文件建立索引，并依赖正确的坐标规则和压缩格式。
- 当问题是“为什么普通 gzip 不行”“为什么 region query / index / fetch 失败”，通常要先回到 `bgzip/tabix` 层。

## 6. grep

主源:

- <https://www.gnu.org/software/grep/manual/grep.html>

提炼:

- `grep` 是按行查找文本的过滤器，适合先确认模式能否命中，再决定是否需要正则或固定字符串匹配。
- 常见入口是 `-n`、`-i`、`-F`、`-E`、`-r`。
- 如果“看起来没报错但就是没结果”，先确认是没命中还是模式写错；`grep` 没命中时退出码通常是 `1`。

## 7. sed

主源:

- <https://www.gnu.org/software/sed/manual/sed.html>

提炼:

- `sed` 是行流编辑器，常用于替换、删除、插入或按行过滤。
- 常见入口是 `-n`、`-i`、`-E`、`-e`、`-f`。
- 如果报 `sed: -e expression #1, char ...`，先看脚本文本是否被 shell 改写或引号断开；复杂脚本通常更适合先写到文件，再用 `-f` 读入。

## 8. awk

主源:

- <https://www.gnu.org/software/gawk/manual/gawk.html>

提炼:

- `awk` 是按字段处理文本的程序，适合做列提取、条件过滤和简单汇总。
- 常见入口是 `-F`、`-v`、`BEGIN`、`END`、`$0`、`$1`。
- 如果字段不对，先确认分隔符是不是 `FS` / `-F` 设错；如果 `$1`、`$2` 看起来被改坏，先确认是否被 shell 提前展开。

## 9. shell quoting / pipeline basics

主源:

- <https://www.gnu.org/software/bash/manual/bash.html>

提炼:

- Shell 层重点是引号、变量展开、转义和管道连接；很多脚本错误其实是 shell 先把命令改写了。
- 单引号保留字面量，双引号保留空格但仍会展开变量和命令替换。
- 管道会把左侧标准输出接给右侧标准输入；要看失败位置时，常需要配合 `set -o pipefail`。
