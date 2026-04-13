# Sengent 2.1 Hosted-LLM Architecture Design

## Core Judgment

`Sengent 2.1` 可以推进，但当前只适合进入 `formal spec` 阶段，不适合直接进入实现阶段。

原因不是方向不清楚，而是方向已经足够清楚，如果不先补齐硬约束，系统很容易 drift 成：

- 更聪明
- 更会说
- 但更松散的半 RAG support bot

所以 `2.1` 的当前目标不是“尽快接上 hosted API”，而是先把 architecture 和 invariants 定死。

## Priority Red Lines

在 `2.1` 正式设计里，必须优先守住两条：

### 1. Hard Constraints Must Land In Spec First

必须先把以下三层写硬，再谈实现：

- `Anti-Drift`
- `Trust Boundary`
- `Tool Arbitration`

如果这三层没有先固化，后面的 hosted runtime 很容易 drift 成 full RAG 风格的 support bot。

### 2. 2.1 Means A Lighter Hosted Runtime, Not A Lighter Governance Core

`2.1` 的定位必须是：

- 更轻的 hosted runtime
- 保留治理内核

可以去掉：

- Ollama 带来的 runtime burden
- 一部分 weak-model compensation

不能丢掉：

- `vendor / domain / playbook / incident` layering
- `build / review / gate / activate / rollback`
- `clarify-first`
- deterministic diagnostics

## Product Definition

`Sengent = a bounded software support agent factory`

`Sengent 2.1` 应被定义为：

`LLM-native, but governance-first`

它不是：

- full-RAG software copilot
- raw-doc direct runtime retrieval bot
- 用模型权重替代正式知识层的 support system

它是：

- 一个利用强托管模型做理解、归纳、澄清、草拟的 software support system
- 一个仍然对当前软件负责、对版本边界负责、对支持边界负责的 support kernel
- 一个未来可承载多个 vendor profile 的内核，而不只是 Sentieon 特化工具

## What 2.1 Must Preserve

这些不是 `2.0` 的历史包袱，而是 `2.1` 的地基：

- `LLM-native, but governance-first`
- 不做 full RAG
- `vendor / domain / playbook / incident` knowledge layering
- `build / review / gate / activate / rollback`
- `clarify-first`
- deterministic diagnostics
- model output is draft until promoted
- runtime 不能把 raw docs 当 truth

## What 2.1 Should Weaken Or Replace

`2.1` 可以弱化或替换的东西主要有三类：

### 1. Local Small-Model Runtime Burden

- Ollama-first runtime assumptions
- local warmup / local model ops burden
- build-only host 仍强依赖本地模型的诊断叙事

### 2. Weak-Model Compensation

- 很多为弱模型兜底的机械路由
- 很重的 prompt 拼装
- 一部分 rigid answer assembly

### 3. Provider Assumption

新的 runtime 假设应是：

- 使用强托管模型
- 内部版先走 `OpenAI-compatible API`
- 先不做复杂 gateway
- 但 adapter 必须保留未来 gateway 接缝

## Non-Goals

`2.1` 第一阶段明确不做：

- raw ingestion 直接进入 runtime truth
- model outputs 直接进入 active packs
- online learning 直接改变 runtime truth
- multi-tenant gateway 平台化
- 第二 vendor 的正式落地
- customer packaging / distribution

## Adversarial Review Upgrades

这是 `2.1` 修订版 spec 必须显式新增的硬层，不允许只停留在口头原则。

### 1. Trust Boundary Layer

必须先定义：

- 什么数据允许发给外部 LLM
- 什么字段必须脱敏
- prompt / trace / logs 如何存储
- 哪些上下文不能出本地

没有这层，`2.1` 一进入 hosted runtime，就会在合规、审计、客户现场数据边界上出问题。

### 2. Tool Arbitration Layer

deterministic diagnostics 不能只是一组工具；在 `2.1` 里，它必须升级成 `hard arbitration layer`。

至少要能回答：

- 哪些问题必须先跑工具
- 哪些问题模型只能解释工具结果
- 哪些问题不能靠模型自由判断

尤其是以下类目必须优先走 tool-first：

- `VCF / BAM / CRAM / BED / FASTA`
- header/index/contig/sort consistency
- 文件结构与格式错误
- deterministic file-state / environment-state checks

### 3. Anti-Drift Invariants

anti-drift 必须从原则升级成系统不变量。至少包括：

- runtime never reads raw ingestion directly as truth
- model output is draft only unless promoted
- tool-required intents cannot be answered from model-only reasoning
- knowledge layers remain explicit
- every evolution path preserves rollback

### 4. Capability-Based LLM Adapter

`2.1` 不能把 adapter 只建模成：

- `base_url`
- `api_key`
- `model`

还必须显式抽象 provider capabilities，例如：

- `supports_tools`
- `supports_json_schema`
- `max_context`
- `supports_reasoning_effort`
- `supports_streaming`
- `prompt_cache_behavior`

原因很简单：

- OpenAI-compatible protocol 相同
- 不等于 provider capability 相同

### 5. Boundary Pack

`2.1` 必须引入显式 `Boundary Pack`，而不是把边界继续散在 prompt 和隐式规则里。

至少包含：

- `should-answer`
- `must-clarify`
- `must-tool`
- `must-refuse`
- `must-escalate`
- version-sensitive boundaries

核心原则：

`Boundary governance should stay strict, but boundary authoring should become low-touch`

也就是：

- 边界治理严格
- 边界编写尽量由模型先归纳、人类后裁决

### 6. Eval / Trace Plane

`2.1` 不能只说“模型更强所以会更好”。

必须显式定义 `eval / trace plane`，至少覆盖：

- factual correctness
- boundary adherence
- clarification quality
- refusal quality
- tool-usage correctness
- evidence fidelity / citation discipline

### 7. Artifact Lifecycle

Knowledge Factory 在 `2.1` 会更强，所以必须定义 artifact lifecycle，否则 draft/candidate 会淹没维护者。

至少包含这些阶段：

- `raw`
- `candidate`
- `review-needed`
- `reviewed`
- `activated`
- `expired`
- `superseded`

## Anti-Drift Invariants

以下不变量必须被视为 `2.1` 的正式红线：

### 1. Runtime Never Reads Raw Ingestion Directly As Truth

runtime 可以读取：

- active knowledge
- explicit compiled layers
- current session context

runtime 不可以直接把以下内容当事实源：

- raw docs
- source inbox
- parsed ingestion bundles
- factory drafts
- model completions

### 2. Model Output Is Draft Only Unless Promoted

模型产物可以影响：

- wording
- clarification
- candidate drafting
- normalization
- contradiction clustering
- dataset drafting

但不能直接成为：

- activated facts
- runtime boundaries
- gate decisions

### 3. Tool-Required Intents Cannot Be Answered From Model-Only Reasoning

对于被 `must-tool` 命中的问题，模型只能：

- 组织工具输出
- 解释工具结果
- 引导下一步

不能绕过工具直接给出“看起来合理”的诊断结论。

### 4. Knowledge Layers Remain Explicit

这些层必须继续是一等公民：

- vendor reference / vendor facts
- vendor decisions
- domain standards
- playbooks / procedures
- troubleshooting / known issues
- incident memory / site memory

### 5. Every Evolution Path Preserves Rollback

无论引入什么 hosted runtime/provider/factory enhancement，都必须保留：

- config rollback
- review rollback
- activation rollback
- pack rollback
- branch/worktree rollback

## Recommended 2.1 Architecture

建议把 `2.1` 总体架构正式写成以下分层：

- Thin Client / CLI
- Support Control Layer
- Boundary Pack + Active Knowledge
- Tool Arbitration Layer
- Deterministic Diagnostics
- Capability-Based LLM Adapter
- Knowledge Factory
- Eval / Trace Plane
- Trust Boundary Layer

### 1. Thin Client / CLI

继续保留 CLI-first operator surface。

负责：

- chat / single-turn entry
- doctor / inspect / review entry
- operator-visible diagnostics

不负责：

- truth governance
- boundary policy ownership

### 2. Support Control Layer

这是 runtime 的核心控制层。

继续负责：

- intent understanding
- clarify-first
- answer contract
- vendor responsibility
- evidence hierarchy

它的核心不是“更自由地回答”，而是：

- 用更强模型在更严格的边界内回答

### 3. Boundary Pack + Active Knowledge

这是 `2.1` 的事实与边界中枢。

它负责定义：

- 能答什么
- 先问什么
- 必须跑工具什么
- 必须拒绝什么
- 必须升级什么

同时，active knowledge 仍然是 runtime truth source。

### 4. Tool Arbitration Layer

这层负责把 deterministic tools 从“可选工具”提升成“决策仲裁器”。

它决定：

- 先 tool 还是先 clarify
- tool 输出能否直接形成 answer evidence
- 模型是否只能解释 tool result

### 5. Deterministic Diagnostics

diagnostics 仍然是一等控制面，不允许被“更强模型”替代。

它继续负责：

- 环境检查
- 文件结构检查
- 格式/索引/一致性检查
- runtime/build role guidance

### 6. Capability-Based LLM Adapter

内部版先用 `OpenAI-compatible` transport，但 adapter contract 必须 capability-based，而不是只看 URL。

最小能力面应包括：

- transport info
- auth info
- capability flags
- max context
- schema / tool / streaming support
- traceability metadata

### 7. Knowledge Factory

`2.1` 最应增强的是 factory，而不是 runtime truth path。

factory 负责：

- ingest
- candidate extraction
- contradiction clustering
- dataset drafting
- boundary drafting

但一律以 `draft + review-required` 进入 lifecycle。

### 8. Eval / Trace Plane

这层必须独立存在，而不是混在日志里。

它负责：

- trace capture
- eval corpus growth
- boundary adherence measurement
- evidence fidelity review

### 9. Trust Boundary Layer

这是 `2.1` hosted direction 的关键新增层。

它负责：

- outbound context filtering
- redaction policy
- prompt / trace retention policy
- local-only context rules
- hosted-provider auditability

## Internal Deployment Recommendation

如果当前阶段只是内部版，推荐路线是：

- 先不要复杂 gateway
- 先做薄的 `OpenAI-compatible + capability-based adapter`
- 通过 env/config 提供 `base_url / api_key / model / provider`
- 给将来挂 LiteLLM / Helicone 这类 gateway 留接缝

明确不要做：

- 在安装包里硬编码共享 API key
- 让 raw docs 直接进入 runtime retrieval truth path

## Phase Judgment

`2.1` 当前阶段判断必须写清楚：

- 可以开始 `research / spec`
- 可以开始 `architecture plan`
- 不要在修订版 spec 完成前直接写 `2.1` 代码

当前最正确的下一步是：

- 在独立 `2.1` worktree 上完成修订版正式 spec
- 固化 anti-drift principles
- spec 稳定后，再写 engineering implementation plan
- 只有在 plan 完成后，才考虑派子线程做 hosted runtime PoC

## Success Criteria For This Tranche

这一 tranche 的成功标准不是“接上 hosted API”，而是：

- `2.1` 的 hosted direction 被写成正式 architecture contract
- anti-drift 被升级成 invariants
- trust boundary、tool arbitration、boundary pack、eval plane、artifact lifecycle 被写成正式层
- 实施顺序被重新约束成 `spec -> plan -> PoC`

## Defining Lines To Keep

这些句子应正式写进 `2.1` 文档并持续沿用：

- `Sengent = a bounded software support agent factory`
- `LLM-native, but governance-first`
- `Boundary governance should stay strict, but boundary authoring should become low-touch`
- `Runtime simplicity must not come from dropping knowledge governance`
- `Sengent may become more model-native, but it must never become raw-retrieval-native`
