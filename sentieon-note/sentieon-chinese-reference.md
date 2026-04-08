# Sentieon Chinese Reference

来源:

- 中文资料站: <https://doc.insvast.com/p/sentieon/>

定位:

- 二线参考资料
- 适合中文表达、培训式概览、平台化流程说明
- 不替代官方文档站、官方 PDF、官方 GitHub

优先级建议:

1. 官方文档站 / 官方 PDF
2. 官方 GitHub
3. 中文资料站

如果三者出现冲突:

- 参数、限制、版本、输出定义，以官方英文资料为准
- 中文资料站用于辅助理解、中文复述和快速导航

## 1. 当前可见内容结构

我整理时在首页看到的主目录包括:

- `Sentieon 中文手册`
- `Sentieon | 发布V202503.01版本`
- `Sentieon软件快速入门指南`
- `Sentieon 软件模块总述`
- `Sentieon 特色流程 - DNAscope`
- `Sentieon 软件应用教程`
- `Sentieon | 泛基因组分析流程详解`
- `Sentieon | 物种全基因组（WGS）分析流程`
- `Sentieon文献解读`

其中 `DNAscope` 分平台内容包括:

- Illumina
- Complete Genomics
- PacBio LongRead
- Ultima Genomics
- Element Bio
- Nanopore LongRead

应用教程区包括:

- HiFi 长读长胚系变异检测
- Sentieon Python API 引擎加速
- 读段组建议
- TNscope 机器学习模型体细胞变异发现
- CCDG 功能等效流程
- 共识功能去除 PCR 重复
- 长读长结构变异检测
- 大型基因组重测序
- 体细胞 SNP/Indel 检测
- DNAscope 机器学习模型胚系变异调用
- UMI
- 分布模式
- CNVscope
- trio 最佳实践
- Segdup-caller

另外还有:

- 泛基因组流程
- 植物和动物 WGS 流程
- 文献解读栏目

## 2. 它最适合做什么

### 中文速读

当线程里需要用中文快速解释 Sentieon 的模块、优势、流程时，这个站更顺手。

### 平台化导航

当问题是“某个平台该看哪个 DNAscope 流程”时，这个站的按平台拆分目录比官方 PDF 更直观。

### 二线支持和培训材料

当需要做内部交接、售前说明、客户中文答疑时，这个站比纯官方手册更接近中文材料风格。

## 3. 不应单独依赖它做什么

以下问题不建议只看中文资料站:

- 精细命令参数默认值
- 最新 release 的能力边界
- 严格的输入输出格式限制
- 分布式、大 cohort、特殊 edge case 的技术判断
- 与 `sentieon-cli` / `sentieon-models` 当前状态强相关的问题

这些仍应回到:

- 官方文档站
- 本地 PDF
- 官方 GitHub

## 4. 和官方源的配合方式

推荐工作流:

1. 先在中文资料站定位中文主题和对应流程
2. 再去官方文档站 / PDF 确认参数、限制、命令
3. 需要脚本或模型时去官方 GitHub

一个稳定的回答口径是:

- 中文资料站帮助快速说明“是什么、适合谁、有哪些流程”
- 官方资料负责确认“具体怎么跑、参数是什么、版本是否支持”

## 5. 对线程 019d5249 的价值

对线程 `019d5249-f1d6-75c0-8d3c-99e3e97e9835`，这份中文资料最有价值的地方是:

- 可以作为中文术语和流程名称的统一口径
- 可以快速按平台定位 DNAscope 相关内容
- 可以补足官方文档不那么“教程化”的部分

建议在该线程里这样使用:

- 先用本目录里的 `thread-019d5249-summary.md` 给出结论
- 需要中文展开说明时，再参考这份中文资料
- 需要严格技术依据时，再回引官方文档或 GitHub

