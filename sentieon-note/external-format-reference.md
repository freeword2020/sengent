# External Format Reference

整理日期: `2026-04-08`

使用边界:

- 这份笔记只整理外部官方格式规范，用于解释文件结构、字段语义、索引和常见兼容性边界。
- 不单独支持 Sentieon workflow 选型，不覆盖 Sentieon 官方 manual / app note 的结论。
- 当问题同时涉及 Sentieon 模块和外部格式时，Sentieon 官方资料仍优先。

## 1. SAM / BAM / CRAM

主源:

- `SAMv1` spec: <https://samtools.github.io/hts-specs/SAMv1.pdf>
- `CRAMv3` spec: <https://samtools.github.io/hts-specs/CRAMv3.pdf>
- `samtools` manual: <https://www.htslib.org/doc/samtools.html>

提炼:

- `SAM` 是文本对齐格式，`BAM` 是其二进制表示，`CRAM` 是参考依赖更强的压缩对齐格式。
- 头信息里常见的是 `@HD`、`@SQ`、`@RG`；很多下游问题都和 header、contig、read group 一致性有关。
- `BAM` 常见索引是 `.bai` 或 `.csi`；`CRAM` 常见索引是 `.crai`。
- 随机访问通常依赖坐标排序和索引；`CRAM` 的解码还经常依赖可用且匹配的参考序列。

## 2. VCF / BCF

主源:

- `VCFv4.5` spec: <https://samtools.github.io/hts-specs/VCFv4.5.pdf>
- `bcftools` manual: <https://www.htslib.org/doc/bcftools.html>

提炼:

- `VCF` 是文本变异记录格式；`BCF` 是更适合程序处理的二进制形式。
- `VCF` 头部由 `##` 元信息行和最后一行 `#CHROM ...` 列标题组成。
- 固定列通常包括 `CHROM`、`POS`、`ID`、`REF`、`ALT`、`QUAL`、`FILTER`、`INFO`；有样本列时还会出现 `FORMAT` 和后续样本数据列。
- `INFO` 是位点级字段，`FORMAT` 是样本级字段。
- 多数需要随机访问或多文件联动的场景，更稳妥的是 `bgzip` 压缩并配 `tabix/CSI` 索引，或直接使用已索引的 `BCF`。

## 3. Read Group

主源:

- `SAMv1` spec: <https://samtools.github.io/hts-specs/SAMv1.pdf>
- `SAMtags` spec: <https://samtools.github.io/hts-specs/SAMtags.pdf>

提炼:

- `Read Group` 通常通过 `@RG` header 行和记录里的 `RG:Z` tag 关联。
- 常见字段包括 `ID`、`SM`、`LB`、`PL` 等；很多下游工具会按 sample 或 read group 聚合。
- 当多个文件 header 里的 `@RG` / `SM` / `ID` 组织不一致时，容易出现样本混淆、合并或下游解释异常。

## 4. BED / Interval

主源:

- `BEDv1` spec: <https://samtools.github.io/hts-specs/BEDv1.pdf>
- `tabix` manual: <https://www.htslib.org/doc/tabix.html>

提炼:

- `BED` 常用于区间选择和 interval 输入。
- `BED` 规范使用 `0-based`、`half-open` 区间；这和 `VCF` / `SAM` 常见的 `1-based` 位置语义不同。
- 做区间联动时要先确认是哪个坐标体系，否则很容易出现“差一位”的现象。
- 如果一个工具要求 `BED` 或可索引区间文件，还要同时确认压缩和索引要求。

## 5. FASTA / FAI

主源:

- `faidx` manual: <https://www.htslib.org/doc/faidx.html>
- `SAMv1` spec: <https://samtools.github.io/hts-specs/SAMv1.pdf>

提炼:

- 参考基因组通常以 `FASTA` 提供，并配 `FAI` 随机访问索引。
- 很多下游链路不仅要求参考序列内容可用，还要求 contig 名、顺序和 companion files 一致。
- 除了 `FAI`，很多链路还会依赖 sequence dictionary（常见是 `.dict`）；这些配套文件最好和 `FASTA` 一起重新生成。
- 当错误集中在 `contig not found`、reference mismatch、CRAM decode 或 region query 时，常要先回到 `FASTA/FAI` 层。
