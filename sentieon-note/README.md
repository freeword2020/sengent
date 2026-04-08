# Sentieon Notes

整理来源:

- 官方文档站: <https://support.sentieon.com/docs/>
- 中文资料站: <https://doc.insvast.com/p/sentieon/>
- 本地 PDF: `Sentieon202503.03.pdf`

版本说明:

- 本地 PDF 文件名是 `Sentieon202503.03.pdf`
- PDF 日期显示为 `Mar 30, 2026`

建议把这份资料当成当前可用的主参考，尤其适合离线查阅和给线程 `019d5249-f1d6-75c0-8d3c-99e3e97e9835` 提供背景。

文件说明:

- `sentieon-modules.json`: 程序优先读取的 Sentieon 模块结构化索引
- `sentieon-module-index.md`: 面向人工阅读的模块总表
- `sentieon-doc-map.md`: 官方文档结构、模块划分、重点章节入口
- `sentieon-github-map.md`: 官方 GitHub 组织、核心仓库、适用场景和与文档站的关系
- `sentieon-chinese-reference.md`: 中文资料站的结构、覆盖主题和使用边界
- `thread-019d5249-summary.md`: 面向当前线程的速查版，优先覆盖安装、许可证、常见流水线、关键限制和排障点

快速结论:

- 如果要回答“模块是什么 / 支持什么输入 / 输出什么 / 相关模块有哪些”，先看 `sentieon-modules.json`
- 如果是 `DNAscope`、`DNAscope LongRead`、`DNAscope Hybrid`、`Joint Call`、`GVCFtyper`、`TNscope` 的高频参数问题，也先看 `sentieon-modules.json`
- 如果是人工浏览模块总表，先看 `sentieon-module-index.md`
- 如果要快速判断用哪个流程，先看 `thread-019d5249-summary.md` 里的“流程选择”
- 如果要补全上下文或追具体命令、参数、章节位置，去看 `sentieon-doc-map.md`
- 如果要找脚本、模型 bundle、容器、云部署样板，先看 `sentieon-github-map.md`
- 如果要找中文表述、培训材料式概览、按平台拆开的流程说明，去看 `sentieon-chinese-reference.md`
- 如果只需找官方原文，优先用本目录里的 PDF 搜索关键词
