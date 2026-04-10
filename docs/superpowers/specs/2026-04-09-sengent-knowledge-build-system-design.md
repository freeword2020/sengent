# Sengent Knowledge Build System Design

## Context

`Sengent` 当前已经形成了可工作的本地支持架构：

- `rule-first` 顶层路由
- `structured knowledge packs` 作为运行时主知识源
- `eval / closed-loop` 作为上线门禁
- 本地 CLI 为主交互入口

当前 `sentieon-note/` 目录中的结构化 JSON 已经能稳定支撑很多参考查询和流程导航，但其维护方式仍然偏人工：

- 新资料需要人工阅读后再手改 JSON
- 资料更新速度依赖少数熟悉代码和 schema 的维护者
- 团队目前更习惯把材料放进 NotebookLM 里阅读、整理和追问，而不是直接维护运行时 pack

因此，系统的下一个瓶颈不是“模型不够强”，也不是“没有向量库”，而是：

- 如何在不破坏现有 `rule-first + structured packs + eval-gated` 架构的前提下
- 明显降低知识更新的人工作量
- 让低编程经验团队也能完成日常资料维护
- 同时为未来复制到其他软件支持 agent 保留通用能力

## Problem Statement

### Problem 1: Raw Docs 与 Runtime Packs 之间缺少产品化编译层

现在 `sentieon-note/*.json` 既是运行时主知识源，也是人工维护结果。这样虽然短期可控，但会带来两个后果：

- 原始文档更新越频繁，人工同步成本越高
- pack schema 越稳定，手工维护越容易形成知识债

### Problem 2: 团队维护习惯偏“投喂资料”，不是“维护结构化数据”

当前团队更熟悉：

- 收集 PDF / markdown / release notes / app notes
- 把资料放到 NotebookLM 中检索和阅读

而不是：

- 理解 pack schema
- 手工切分条目
- 手工维护编译产物

如果下一步方案仍要求团队直接改 JSON、调 chunk、修向量库，就算技术上成立，维护上也会失败。

### Problem 3: Full RAG 会引入错误方向的复杂度

将运行时主知识源改成通用向量检索，会带来新的问题：

- chunk 设计、去重、版本冲突、引用漂移
- 检索召回与排序调优
- prompt coupling 和答案可解释性下降
- evaluation 从“pack 行为回归”变成“检索分布 + 生成行为回归”

这与当前架构的核心原则冲突：

- runtime 主知识源应保持可控
- top-level route 不交给 LLM
- 新坏例子优先进 eval / feedback

## Design Goal

建设一个**低人工维护的知识编译系统**，把团队的日常工作收敛为：

1. 投递原始资料
2. 查看 build 报告
3. 只处理少量异常项

而不是让团队直接维护运行时 JSON 或向量库。

## Core Principles

### 1. Runtime 继续吃 Structured Packs，不直接吃 Raw Docs

运行时主路径保持不变：

- `support_coordinator` 继续做顶层任务选择
- `reference_intents` / `reference_resolution` 继续做确定性 reference 路径
- `sentieon-note/*.json` 继续做运行时主知识源

raw docs 不直接进入主运行时路由。

### 2. Raw Docs 成为事实源，Compiler 负责把事实编译成 Pack

资料更新不再等于“手改 pack”，而是：

- 文档进入 raw corpus
- parser 产生 canonical representation
- compiler 将 canonical representation 编译成运行时 packs

### 3. Folder-In, Report-Out

对普通维护者，系统的主要交互必须是：

- 把资料丢进固定目录
- 或通过 `knowledge scaffold` 生成/补全资料模板
- 运行一次 build
- 用 `knowledge review` 查看最新 build 报告

### 4. No Manual Pack Editing for Normal Maintainers

普通维护者不应直接编辑：

- `sentieon-modules.json`
- `workflow-guides.json`
- `external-*.json`

只有少数技术 owner 才能处理编译器规则或异常修复。

### 5. Exception-First Review

系统不要求人工全量审核所有提取结果，只要求审核：

- 解析失败项
- 低置信项
- 冲突项
- 影响 eval gate 的高风险变更

### 6. Eval-Gated Activation

任何新 pack 都不能直接替换当前运行时知识源。

必须先通过：

- schema validation
- source diff / pack diff
- pilot readiness
- pilot closed loop

之后才允许激活。

### 7. Portable Build Core

知识编译系统应当尽量通用，便于未来复制到其他软件支持 agent：

- 通用部分：ingest / parse / compile runtime / review report / eval gate
- 产品特定部分：schema mapping、pack compiler 规则、eval corpus

同时，交付默认应以**安装后的 `sengent` 命令**为操作入口，而不是开发态 `PYTHONPATH=src` 命令。

P1 收紧后的默认路径策略：

- app home:
  - macOS: `~/Library/Application Support/Sengent`
  - Linux: `$XDG_DATA_HOME/sengent` 或 `~/.local/share/sengent`
- active source packs: `<app-home>/sources/active`
- knowledge inbox: `<app-home>/knowledge-inbox/sentieon`
- build root: `<app-home>/runtime/knowledge-build`

这样做的原因是：

- 安装后的运行时不再依赖 repo checkout 的目录结构
- build / activate / rollback 可以在用户自有目录中独立运行
- 未来复制到其他产品时，目录契约更稳定

## Recommended Direction

推荐采用：

`Docling + self-owned compiler + optional Crawl4AI later`

而不是引入 full-RAG 平台。

### Why Docling

`Docling` 适合当前阶段的原因：

- 支持本地 / air-gapped 运行
- 对复杂 PDF 的理解能力强于轻量 markdown converter
- 输出适合进入 canonical representation，而不强绑定某个 RAG runtime
- 不会把系统架构带偏成“先切 chunk 再向量检索”

### Why Not Full Knowledge Platforms

像 `RAGFlow`、`Onyx`、`Dify`、`AnythingLLM` 这类整套知识平台，虽然产品化程度高，但产品化的重点是：

- 搜索
- 向量检索
- knowledge chat
- agent orchestration

这不是当前 Sengent 的主问题。当前主问题是**如何低人工地生成可控的 structured packs**。

## Target Architecture

### 1. Raw Source Layer

维护者把原始资料投递到一个固定目录，例如：

- `knowledge-inbox/sentieon/`

支持的输入类型包括：

- PDF
- Markdown
- HTML
- shell scripts
- release notes
- app notes
- NotebookLM 导出的材料

每个输入资料至少要能关联以下元信息：

- `source_type`
- `origin`
- `product`
- `version`
- `date`
- `language`
- `license_hint`

P0 不要求维护者手写复杂 manifest，可以允许：

- 文件名约定
- 简单 sidecar metadata
- 或 build 时自动生成缺省 metadata，再在报告里提示补齐

当前实现里，sidecar metadata 采用与原文同目录的 `*.meta.yaml` / `*.meta.yml` 约定：

- 原始文档保持原样
- sidecar 只补缺失字段
- front matter 若已显式给值，则 sidecar 不静默覆盖
- 删除不通过手改 active pack 完成，而是通过显式 `action: delete` 的 retirement stub 进入 candidate build

### 2. Ingest Layer

P0 只支持本地离线 ingest：

- 扫描本地目录
- 识别文件类型
- 建立 build inventory

P1 可加入 `Crawl4AI` 做 docs site snapshot：

- 只做资料抓取
- 不直接进入运行时回答链路

P2 再预留云端采集 API。

### Packaging Contract

P1 交付要求里，build runtime 的依赖契约必须显式化：

- `PyYAML` 为 mandatory dependency
- `docling` 为 optional PDF build dependency

也就是说：

- 没有 `PyYAML`，当前 CLI/knowledge build 不应被视为可安装成功
- 没有 `docling`，系统仍可运行，但 PDF 资料会进入异常队列，而不是静默参与编译

### 3. Canonical Parse Layer

P0 推荐：

- `Docling` 作为主 parser
- `MarkItDown` 作为轻量格式 fallback

`MinerU` 只作为复杂 PDF 的 benchmark 或补充方案，不作为 P0 主线。

这一层的输出不是 runtime pack，而是统一的 canonical records，例如：

- 文档级 record
- section / chunk 级 record
- code block / command block 级 record
- table / parameter candidate 级 record

### 4. Canonical Build Artifacts

建议所有 build 先输出到本地 build 目录，例如：

- `runtime/knowledge-build/<build_id>/inventory.json`
- `runtime/knowledge-build/<build_id>/canonical_doc_record.jsonl`
- `runtime/knowledge-build/<build_id>/canonical_section_record.jsonl`
- `runtime/knowledge-build/<build_id>/script_candidate_record.jsonl`
- `runtime/knowledge-build/<build_id>/parameter_candidate_record.jsonl`
- `runtime/knowledge-build/<build_id>/parameter_promotion_review.jsonl`
- `runtime/knowledge-build/<build_id>/parameter_review_suggestion.jsonl`
- `runtime/knowledge-build/<build_id>/report.md`
- `runtime/knowledge-build/<build_id>/exceptions.jsonl`

这些目录保持本地运行时属性，不提交 git。

### Managed Pack Completeness Guard

P1 还需要把 managed pack 完整性变成显式护栏。

在以下阶段，系统都必须拒绝不完整的 managed pack 集合：

- `knowledge build` 读取 active source dir 时
- `knowledge activate` 读取 candidate packs 时
- `knowledge rollback` 读取 backup 时

理由很直接：

- 不完整的 source pack 集会污染 diff 和 backup 语义
- 不完整的 candidate pack 集会把“缺文件”误解释成“应该删除”
- 不完整的 backup 不能被当成可恢复版本

### 5. Pack Compiler Layer

compiler 从 canonical records 生成当前运行时 packs：

- `sentieon-modules.json`
- `workflow-guides.json`
- `external-format-guides.json`
- `external-tool-guides.json`
- `external-error-associations.json`

P0 只要求第一版 compiler 能支持：

- 模块简介 / 参数 / 脚本 / 输入输出
- workflow guidance
- external format/tool/error notes 的基础提取

后续阶段可以继续增加“review-first”提取层，例如：

- script candidate extraction
- parameter candidate extraction

但这些候选不应自动等价于 runtime 主知识。当前实现里更保守：

- 高置信 script candidate 可以作为 `script_examples` 进入 module candidate pack
- parameter candidate 不会直接变成 runtime knowledge
- module 参数只有在维护者提供显式结构化 metadata 时才允许进入 candidate pack
- `parameter_promotion_review.jsonl` 和 `report.md` 会把“已晋升参数”和“高置信但未晋升参数”分开列出，供 technical owner 审核
- `parameter_review_suggestion.jsonl` 会只为真正缺口生成可填写的 metadata template
- 如果 active packs 已经在当前 module 或共享 `sentieon-cli` module 覆盖了某个参数，build report 会把它降噪为“已覆盖”，而不是继续骚扰维护者
- `knowledge scaffold` 负责为 add/update/delete 创建或补全安全的 markdown + sidecar 模板，避免维护者手写 schema
- `knowledge review` 负责把最近一次 build 的 `report.md` 直接暴露成维护入口，而不是让维护者自己翻 artifact 目录

P0 不追求完全自动化抽取所有细节，而追求：

- 自动产出基础结构
- 稳定保留来源引用
- 把无法自动确定的内容显式送入异常队列

### 6. Review Report Layer

报告必须面向低编程经验维护者，而不是面向编译器开发者。

报告至少要包含：

- 本次 ingest 识别了多少文档
- 哪些文档解析失败
- 哪些文档缺元信息
- 哪些模块 / workflow / external guide 有新增或变化
- 哪些条目低置信
- 哪些条目被跳过
- 本次变更会影响哪些运行时 pack

核心要求：

- 报告要异常优先
- 维护者只需要关注变化和异常，不需要通读全部中间产物

### 7. Exception Queue

异常队列是整套系统低人工维护的关键。

异常项应包括：

- parse failure
- malformed front matter / document parse error
- malformed sidecar metadata
- metadata missing
- duplicated candidates
- conflicting version claims
- parameter extraction ambiguity
- script skeleton extraction ambiguity
- unsupported document pattern

只有这些异常需要进入少数技术 owner 的处理范围。

当前实现里，`knowledge build` 必须满足 exception-first：

- 单个坏文档、坏 front matter、坏 sidecar 只能进入 exception queue
- 不允许因为一份坏资料让整个 build、report、candidate packs 直接中断
- 维护者永远应该能拿到本次 build 的 report 和异常列表

### 8. Eval Activation Gate

compiler 的产物先生成 candidate packs，而不是直接覆盖当前 active packs。

激活前需要通过：

- schema validation
- diff summary
- `python3.11 scripts/pilot_readiness_eval.py`
- `python3.11 scripts/pilot_closed_loop.py`

未通过 gate 的 candidate packs 不得激活。

当前实现里，candidate-source gate 会把 machine-readable 报告写回 build 目录，例如：

- `runtime/knowledge-build/<build_id>/pilot-readiness-report.json`
- `runtime/knowledge-build/<build_id>/pilot-closed-loop-report.json`

只有这两份 gate report 都明确 `ok=true`，`knowledge activate` 才允许把 candidate packs 提升为 active packs，并写 activation manifest。

当前实现里，激活还必须带版本化保险丝：

- `knowledge activate` 在覆盖 active packs 之前，会先把当前 active source packs 完整快照到 `runtime/knowledge-build/activation-backups/<backup_id>/`
- activation manifest 必须显式记录 `backup_id`
- 本地默认只保留最近 `3` 个 activation backup，旧备份自动轮转删除
- `knowledge rollback --backup-id <backup_id>` 只负责把指定 backup 精确恢复回 active source packs，不重新 build，也不绕过 gate
- activation/rollback 都必须按 managed pack 集合做 exact restore，不能留下“激活后新增但回滚未删除”的残留文件
- activation 过程中若 live apply 失败，系统必须优先恢复激活前快照，而不是把 active source 留在 mixed state
- rollback 失败时必须明确指出是 `backup not found` 还是 `backup incomplete`，而不是静默继续

operator-facing 命令还必须满足：

- `knowledge build`
- `knowledge activate`
- `knowledge rollback`

在未显式传 `--source-dir` 时，默认回落到当前配置的 active source dir，而不是因 `Path(None)` 崩溃。

`knowledge review` 的 latest build 选择也必须只看真正的 build 目录，不能把 `activation-backups/` 这类 support 目录误判成 latest build。

### 9. Optional Retrieval Sidecar

后续可增加 retrieval sidecar，但边界必须明确：

- 用于 coverage discovery
- 用于 source lookup
- 用于低置信 fallback evidence assist

不得承担：

- top-level route
- 参数问答主路
- workflow handoff 主路
- script skeleton 主路

## Human Roles

### 1. Normal Maintainer

负责：

- 投递资料
- 运行 build
- 查看报告
- 在 `ready_to_apply` 时执行 activation
- 如激活后发现问题，执行指定 `backup_id` 的 rollback
- 标记少量明显异常

不负责：

- 修改 compiler 规则
- 修改 runtime packs
- 调整 parser 参数
- 处理复杂 schema 问题

### 2. Technical Owner

负责：

- compiler 规则修正
- parser fallback 策略
- 异常项处理
- 激活候选 pack

### 3. Runtime Owner

负责：

- eval gate
- closed-loop 结果审查
- active pack 发布

这三个角色在小团队里可以部分重叠，但设计上必须区分，避免把所有负担落到普通维护者身上。

### Runtime Feedback Compatibility

closed-loop runtime feedback intake 必须兼容两类记录：

- 新格式：`session_id + selected_turn_ids`
- 旧格式：内嵌 `captured_turns`

这样才能保证：

- 历史反馈不会因为 schema tightening 被静默降级成 `pending`
- feedback JSONL 单独导出时，仍可通过显式 `runtime_root` 继续 replay
- 试点评分链路不会因为路径推断失败而漏掉 runtime feedback

## P0 Scope

P0 只做最小但完整的一条链：

1. 建立本地 `knowledge-inbox` 约定
2. 集成 `Docling` 作为主 parser
3. 定义 canonical JSONL schema
4. 实现第一版 compiler，生成 candidate packs
5. 生成异常优先的 build report
6. 用现有 eval / closed-loop 做 activation gate

P0 不做：

- 向量数据库主路
- full-RAG runtime
- 云端采集主依赖
- 多租户知识平台
- 通用 agent 平台化

## P0 User Experience

P0 成功时，普通维护者的操作应当像这样：

1. 把新资料放进 `knowledge-inbox/sentieon/`
2. 运行一次 build 命令
3. 打开生成的 `report.md`
4. 如果没有高风险异常，就交给 technical owner 激活

系统不应要求普通维护者：

- 手改 pack JSON
- 修改代码
- 理解 parser / compiler internals

## Success Metrics

### Maintenance Metrics

- 普通维护者一次资料更新的标准操作不超过 10 分钟
- 80% 以上的资料更新无需修改代码
- 80% 以上的资料更新无需直接编辑 runtime packs
- 维护者只需处理异常队列，而不是全量审核中间产物

### Architecture Metrics

- runtime 仍然以 structured packs 作为主知识源
- top-level route 不引入 LLM 主路
- eval / closed-loop 仍然是激活门禁
- raw docs 与 runtime pack 之间存在清晰可追溯的 compiler contract

### Portability Metrics

- 将来为其他软件复制时，只需替换：
  - product-specific parser hints
  - compiler mapping rules
  - eval corpus

而不需要重做整个 build runtime。

## Non-Goals

- 用 full RAG 替换当前 runtime 主知识源
- 让维护者直接操作向量库
- 在 P0 引入云端采集依赖
- 在 P0 做通用知识平台产品化
- 在 P0 追求零人工审查

## Risks

### Risk 1: 过度乐观估计自动提取质量

复杂 PDF、跨页表格、参数表、长 shell pipeline 不会在第一版里 100% 自动提取正确。

缓解方式：

- exception queue
- parser fallback
- candidate-only activation

### Risk 2: Compiler 变成新的手工负担

如果 compiler 写得过于产品特化、过于脆弱，会把人工成本从“改 pack”转移成“修编译器”。

缓解方式：

- P0 只覆盖高价值、稳定结构
- 低置信内容先不自动入 pack
- 优先保守，不追求一次性全自动

### Risk 3: 团队仍被迫理解内部细节

如果没有报告层和异常队列，维护者仍会被迫阅读 canonical JSONL 或 candidate packs。

缓解方式：

- 报告必须面向维护者
- 中间产物只作为技术兜底使用

## Recommendation

下一步正式实施时，应该以以下目标推进：

**保留当前 `rule-first + structured packs + eval-gated` runtime，新增一个 `Docling-centered`, low-human-maintenance knowledge build system。**

这是对现有架构的增强，不是对现有架构的替代。
