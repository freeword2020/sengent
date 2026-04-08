# Sentieon Notes

整理来源:

- 官方文档站: <https://support.sentieon.com/docs/>
- 中文资料站: <https://doc.insvast.com/p/sentieon/>
- 本地 PDF: `Sentieon202503.03.pdf`

版本说明:

- 本地 PDF 文件名是 `Sentieon202503.03.pdf`
- PDF 日期显示为 `Mar 30, 2026`

这份资料可作为当前本地参考，适合离线查阅和给线程 `019d5249-f1d6-75c0-8d3c-99e3e97e9835` 提供背景。

文件说明:

- `sentieon-modules.json`: 程序读取的 Sentieon 模块结构化索引
- `workflow-guides.json`: 程序读取的流程分流索引，覆盖 workflow guidance 和短 follow-up 归一化后的确定性回答
- `external-format-guides.json`: 程序读取的外部格式规范索引，仅用于格式/字段/索引/结构说明
- `external-tool-guides.json`: 程序读取的外部工具文档索引，仅用于工具定位、报告含义和排错关联
- `external-error-associations.json`: 程序读取的外部错误关联索引，仅用于把高频报错归到格式/工具层
- `sentieon-module-index.md`: 面向人工阅读的模块总表
- `sentieon-script-index.md`: 当前参考命令 / 参考脚本覆盖范围和来源说明
- `sentieon-doc-map.md`: 官方文档结构、模块划分、重点章节入口
- `sentieon-github-map.md`: 官方 GitHub 组织、主要仓库和与文档站的关系
- `external-format-reference.md`: 面向人工阅读的外部格式规范笔记和官方来源
- `external-tool-reference.md`: 面向人工阅读的外部工具文档笔记和官方来源
- `external-error-reference.md`: 面向人工阅读的外部错误关联笔记和官方来源
- `sentieon-chinese-reference.md`: 中文资料站的结构、覆盖主题和使用边界
- `thread-019d5249-summary.md`: 面向当前线程的速查版，汇总安装、许可证、常见流水线、限制和排障点

快速结论:

- 如果要回答“模块是什么 / 支持什么输入 / 输出什么 / 相关模块有哪些”，看 `sentieon-modules.json`
- 如果是 `sentieon-cli` / `sentieon driver` 常见通用参数问题，例如 `-t`、`-r`，也看 `sentieon-modules.json`
- 如果是 `DNAscope`、`DNAscope LongRead`、`DNAscope Hybrid`、`Sentieon Pangenome`、`CNVscope`、`Joint Call`、`GVCFtyper`、`TNscope` 的参数问题，也看 `sentieon-modules.json`
- 如果是 `GeneEditEvaluator` 的参数或脚本问题，也先看 `sentieon-modules.json`
  - 当前会稳定说明“本地官方资料只有 release notes 级提及”，不会凭空补命令
- 如果要回答“有没有参考脚本 / 参考命令”，看 `sentieon-script-index.md` 和 `sentieon-modules.json`
  - 当前已覆盖 `RNAseq`、`DNAseq`、`DNAscope`、`DNAscope LongRead`、`DNAscope Hybrid`、`Sentieon Pangenome`、`CNVscope`、`TNscope`、`Joint Call`
  - `GeneEditEvaluator` 当前只覆盖“脚本缺失状态说明”，还没有真实 command skeleton
- 如果是“流程怎么走 / 这种 follow-up 该切到哪条 workflow”的问题，看 `workflow-guides.json`
  - 当前已覆盖 `WGS/WES/panel` 的 paired/unpaired somatic follow-up
  - 当前也覆盖输入形态 follow-up，例如 `FASTQ`、`BAM/CRAM`
  - `long-read` 场景已覆盖平台 follow-up，例如 `ONT`、`HiFi`
- 如果是人工浏览模块总表，看 `sentieon-module-index.md`
- 如果是 `VCF/BCF`、`SAM/BAM/CRAM`、`Read Group`、`BED/interval`、`FASTA/FAI` 的字段、结构、索引问题，看 `external-format-guides.json`
- 如果是 `samtools`、`bcftools`、`FastQC`、`MultiQC`、`bgzip/tabix` 的定位、报告含义和高频排错入口，看 `external-tool-guides.json`
- 如果是 `grep`、`sed`、`awk`、`shell quoting / pipeline basics` 的定位、常用入口和脚本常见误区，看 `external-tool-guides.json`
- 如果是“更像哪一层出错”的高频格式/工具报错归因，看 `external-error-associations.json`
  - 当前已覆盖 `bgzip/tabix`、`Read Group/header`、`CRAM/reference mismatch`
  - 当前也覆盖 `contig naming / sequence dictionary`、`BED 坐标体系`、`FASTA/FAI/dict` 配套不一致、`BAM sort/index` 状态
  - 还覆盖 `grep` 正则 / 固定字符串误用、`sed` quoting / 原地修改、`awk` 字段分隔符 / shell 展开、`shell` 引号 / 管道语义
- 如果需要查看这些外部资料的人工整理说明和官方来源，看 `external-format-reference.md`、`external-tool-reference.md`
  - 错误关联说明在 `external-error-reference.md`
- 如果要快速查看当前线程汇总，看 `thread-019d5249-summary.md`
- 如果要补全上下文或追具体命令、参数、章节位置，看 `sentieon-doc-map.md`
- 如果要找脚本、模型 bundle、容器、云部署样板，看 `sentieon-github-map.md`
- 如果要找中文表述、培训材料式概览、按平台拆开的流程说明，看 `sentieon-chinese-reference.md`
- 如果只需找官方原文，用本目录里的 PDF 搜索关键词

边界说明:

- 外部格式/工具资料层只用于解释通用格式规范、工具定位和排错关联。
- 它们不会单独承担 Sentieon workflow 选型，也不会覆盖 Sentieon manual / app note 的主结论。
