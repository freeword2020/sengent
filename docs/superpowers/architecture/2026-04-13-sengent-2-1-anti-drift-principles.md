# Sengent Anti-Drift Principles

## Core Line

`LLM-native, but governance-first`

## Red Line

`Sengent may become more model-native, but it must never become raw-retrieval-native.`

## Product Boundary

`Sengent` 不是“读文档的聊天机器人”。

它是一个 `bounded software support agent factory`：

- runtime 负责在受控边界内理解、澄清、回答
- compiler 负责 build / review / gate / activate / rollback
- factory 负责 ingest、candidate drafting、normalization、boundary drafting

## System Invariants

### 1. Runtime Never Reads Raw Ingestion Directly As Truth

runtime truth 只能来自：

- active knowledge
- explicit compiled layers

不能直接来自：

- raw docs
- source inbox
- parsed ingestion bundles
- factory drafts
- model completions

### 2. Model Output Is Draft Only Unless Promoted

模型输出可以成为：

- answer wording
- clarification wording
- candidate artifacts
- contradiction clusters
- dataset drafts
- boundary drafts

模型输出不可以直接成为：

- activated facts
- runtime boundaries
- gate decisions

### 3. Tool-Required Intents Cannot Be Answered From Model-Only Reasoning

以下类问题必须优先进入 deterministic tool path：

- `VCF / BAM / CRAM / BED / FASTA`
- header/index/contig/sort consistency
- 文件结构/格式错误
- deterministic environment/file-state checks

模型只能解释工具结果，不能绕过工具直接给结论。

### 4. Knowledge Layers Remain Explicit

以下层必须继续被视为一等公民：

- vendor reference / vendor facts
- vendor decisions
- domain standards
- playbooks / procedures
- troubleshooting / known issues
- incident memory / site memory

### 5. Every Evolution Path Preserves Rollback

以下 rollback 必须继续存在：

- config rollback
- review rollback
- activation rollback
- pack rollback
- branch/worktree rollback

### 6. Runtime Simplicity Must Not Come From Dropping Governance

可以简化：

- small-model compensation logic
- heavy prompt assembly
- local runtime ops burden

不可以简化：

- review
- audit
- truth source discipline
- boundary ownership

### 7. Hosted Direction Requires Trust Boundary Discipline

在把上下文发给外部 LLM 之前，系统必须明确：

- 哪些字段允许出站
- 哪些字段必须脱敏
- trace / prompt / logs 怎么存
- 哪些上下文必须 local-only

## Architectural Consequences

这些不变量直接意味着：

- hosted provider 接口必须先落在 adapter seam，而不是 retrieval shortcut
- tool arbitration 必须成为硬控制层
- boundary pack 必须显式存在
- knowledge factory 可以更强，但只能输出 `review-needed` artifacts
- eval / trace plane 必须单列，而不是隐含在运行日志里

## Review Checklist

每个 `2.1` 设计或实现都应该过这组问题：

1. 这个改动有没有让 runtime 更接近 raw retrieval truth path？
2. 这个改动有没有让模型输出更接近直接激活的事实？
3. 这个改动有没有允许 tool-required intent 跳过 deterministic tools？
4. 这个改动有没有弱化显式知识分层？
5. 这个改动有没有让 rollback 更模糊？
6. 这个改动有没有把敏感上下文不受控地送出本地？

只要其中任一项偏向 “yes”，这个改动就不应直接进入主线实现。
