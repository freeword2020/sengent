# External Error Association Reference

整理日期: `2026-04-08`

使用边界:

- 这份笔记只整理“更像是哪一类格式/工具层问题”的确定性关联，不直接替代现场复现。
- 这里的关联判断优先回答“先看哪一层”，而不是替代 Sentieon manual、工具手册或真实输入文件检查。
- 如果问题已经明确落在 Sentieon 官方模块、workflow 或 app note 范围，仍以 Sentieon 官方资料为主。

## 1. 普通 gzip VCF / BED 无法 tabix 索引

主源:

- `bgzip`: <https://www.htslib.org/doc/bgzip.html>
- `tabix`: <https://www.htslib.org/doc/tabix.html>

关联原则:

- 当用户提到“普通 gzip”“tabix 建不了索引”“region query / fetch 失败”时，优先关联到 `bgzip/tabix` 层。
- 这类问题通常先检查压缩方式、排序状态、坐标规则和索引文件是否匹配。

## 2. Read Group / sample header 不一致

主源:

- `SAMv1`: <https://samtools.github.io/hts-specs/SAMv1.pdf>
- `SAMtags`: <https://samtools.github.io/hts-specs/SAMtags.pdf>
- `samtools`: <https://www.htslib.org/doc/samtools.html>

关联原则:

- 当用户提到 `read group`、`@RG`、`RGID`、sample/header 不一致时，优先关联到 `Read Group` 层。
- 这类问题通常先检查 header 里的 `@RG` 字段和记录上的 `RG:Z` tag 是否稳定、成套。

## 3. CRAM decode / reference mismatch

主源:

- `CRAMv3`: <https://samtools.github.io/hts-specs/CRAMv3.pdf>
- `faidx`: <https://www.htslib.org/doc/faidx.html>
- `samtools`: <https://www.htslib.org/doc/samtools.html>

关联原则:

- 当用户提到 `CRAM decode`、`reference mismatch`、`contig not found` 时，优先看 `FASTA/FAI` 和 `SAM/BAM/CRAM` 层。
- 这类问题通常要先确认参考序列、索引、contig 名称和输入文件的一致性。

## 4. Contig naming / sequence dictionary mismatch

主源:

- `SAMv1`: <https://samtools.github.io/hts-specs/SAMv1.pdf>
- `VCFv4.5`: <https://samtools.github.io/hts-specs/VCFv4.5.pdf>
- `faidx`: <https://www.htslib.org/doc/faidx.html>

关联原则:

- 当用户提到 `contig not found`、`chr1/1`、`MT/M`、`sequence dictionary mismatch`、`@SQ` 不一致时，优先关联到 contig / dictionary 一致性层。
- 这类问题通常先检查 `FASTA`、`FAI`、`dict`、`VCF/BAM/CRAM header` 是否真的使用同一套 contig 名和顺序。

## 5. BED / interval 坐标体系不一致

主源:

- `BEDv1`: <https://samtools.github.io/hts-specs/BEDv1.pdf>
- `tabix`: <https://www.htslib.org/doc/tabix.html>

关联原则:

- 当用户提到 `BED`、`interval`、区间“差一位”“偏一位”或 region 命中异常时，优先看坐标体系是否混用了 `0-based half-open` 和 `1-based` 语义。
- 这类问题通常先确认区间文件格式、坐标转换历史，以及下游工具参数到底期望哪种区间定义。

## 6. Reference FASTA / FAI / dict 配套文件不一致

主源:

- `faidx`: <https://www.htslib.org/doc/faidx.html>
- `SAMv1`: <https://samtools.github.io/hts-specs/SAMv1.pdf>

关联原则:

- 当用户提到 `FASTA`、`FAI`、`dict` 对不上、sequence dictionary 冲突、reference companion files 过期时，优先关联到参考配套文件一致性层。
- 这类问题通常先检查是否替换过 `FASTA` 但继续沿用了旧 `FAI` / `dict`，以及 companion files 是否与当前 reference 同步生成。

## 7. BAM 排序 / 索引状态异常

主源:

- `samtools`: <https://www.htslib.org/doc/samtools.html>
- `SAMv1`: <https://samtools.github.io/hts-specs/SAMv1.pdf>

关联原则:

- 当用户提到 `BAM` 不能随机访问、`region query` 失败、怀疑“没排序/没索引”时，优先看排序和索引状态。
- 这类问题通常先确认文件是否为 coordinate-sorted、索引是否存在且匹配当前 `BAM` 内容，以及 header / contig 组织是否与索引兼容。

## 8. CRAM 随机访问 / CRAI 状态异常

主源:

- `samtools`: <https://www.htslib.org/doc/samtools.html>
- `CRAMv3`: <https://samtools.github.io/hts-specs/CRAMv3.pdf>

关联原则:

- 当用户提到 `CRAM` 不能随机访问、`crai` 缺失、`region query` 失败时，优先看 CRAM 的随机访问和索引状态，而不是直接归到 `BAM sort/index`。
- 这类问题通常先检查 `.crai` 是否存在且匹配当前 `CRAM`，再区分这是索引状态问题还是更深的 reference / decode 问题。

## 9. grep 正则 / 固定字符串语义不一致

主源:

- `grep`: <https://www.gnu.org/software/grep/manual/grep.html>

关联原则:

- 当用户提到 `grep`、`regex`、`-F`、`-E`、`fixed string`、`匹配不到` 或“有结果但就是不对”时，优先看 grep 的匹配语义。
- 这类问题通常先确认是固定字符串还是正则，再检查 shell quoting 有没有把模式改写掉。

## 10. sed 脚本 quoting / 原地修改误用

主源:

- `sed`: <https://www.gnu.org/software/sed/manual/sed.html>

关联原则:

- 当用户提到 `sed`、`-i`、`-e`、`-f`、`expression`、`unknown command`、`unterminated` 或 `extra characters` 时，优先看脚本文本本身有没有被 shell 改写。
- 这类问题通常先确认 `sed` 表达式是否被正确引用，以及 `-i` 是否真的适合当前场景。

## 11. awk 字段分隔符 / shell 展开问题

主源:

- `awk`: <https://www.gnu.org/software/gawk/manual/gawk.html>

关联原则:

- 当用户提到 `awk`、`-F`、`FS`、`$1`、`syntax error`、`missing }` 或字段不对时，优先看字段分隔符和程序引用方式。
- 这类问题通常先确认 awk 程序有没有被单引号包住，以及 shell 变量是否应该通过 `-v` 传入。

## 11. shell 引号 / 管道语义错误

主源:

- `bash`: <https://www.gnu.org/software/bash/manual/bash.html>

关联原则:

- 当用户提到 `shell`、`bash`、`quote`、`quoting`、`引号`、`管道`、`pipefail`、`unexpected EOF`、`matching quote` 或 `command not found` 时，优先看 shell 解析和管道连接。
- 这类问题通常先检查引号是否配对、是否需要额外转义、以及管道失败是否被 `pipefail` 掩盖。
