# Sengent 2.1 Anti-Drift Principles

## Core Line

`LLM-native, but governance-first`

## Red Line

`Sengent may become more model-native, but it must never become raw-retrieval-native.`

## Product Boundary

`Sengent` 不是“读文档的聊天机器人”。

它是一个 `bounded software support agent factory`：

- runtime 负责在受控边界内理解、澄清、回答
- compiler 负责 build / review / gate / activate / rollback
- factory 负责低触达、高治理的 knowledge drafting

## Non-Negotiable Rules

### 1. Runtime Never Reads Raw Ingestion As Truth

runtime 不可以把这些对象直接当事实层：

- raw vendor docs
- parsed source bundles
- source inbox
- factory drafts
- model completions

runtime truth 只能来自：

- active knowledge
- explicit compiled layers

### 2. Model Outputs Are Drafts, Never Truth

模型输出可以是：

- answer wording
- clarification wording
- candidate artifacts
- normalization drafts
- contradiction clusters
- dataset drafts

模型输出不可以直接是：

- activated facts
- gate decisions
- official runtime boundaries

### 3. Knowledge Layers Stay Explicit

以下层必须继续被视为一等公民：

- vendor reference / vendor facts
- vendor decisions
- domain standards
- playbooks / procedures
- troubleshooting / known issues
- incident memory / site memory

更强模型不能把这些层重新压扁成“检索到什么就算什么”。

### 4. Clarify Before Guess

如果证据不足，优先澄清。

不允许因为 hosted model 更强，就在版本、输入、workflow、支持边界不清楚时直接猜。

### 5. Every Evolution Path Preserves Rollback

以下 rollback 必须继续存在：

- config rollback
- pack rollback
- activation rollback
- review rollback
- branch/worktree rollback

### 6. Runtime Simplicity Must Not Come From Dropping Governance

可以简化：

- 小模型补丁式 prompt
- local model ops burden
- mechanical response assembly

不可以简化：

- review
- audit
- boundary ownership
- truth source discipline

## Architectural Consequences

这些原则直接意味着：

- hosted provider 接口应先落在 adapter seam，而不是检索层捷径
- runtime/provider 升级优先级高于 raw retrieval 扩张
- factory 应更强，但只能输出 `review_required` drafts
- doctor/diagnostics 必须继续是一等控制面

## Review Questions

每个 `2.1` 设计或实现都应该过这组问题：

1. 这个改动有没有让 runtime 更接近 raw retrieval truth path？
2. 这个改动有没有让模型输出更接近直接激活的事实？
3. 这个改动有没有弱化显式知识分层？
4. 这个改动有没有让 clarify-first 退化成 guess-first？
5. 这个改动出了问题时，rollback 路径是否仍然清楚？

只要其中任一项答案偏向 “yes”，这个改动就不应直接进入主线实现。
