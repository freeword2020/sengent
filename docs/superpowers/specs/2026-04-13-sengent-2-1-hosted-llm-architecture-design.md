# Sengent 2.1 Hosted-LLM Architecture Design

## Goal

定义 `Sengent 2.1` 的第一版正式架构：让系统可以直接使用强托管模型做 runtime understanding 和 offline factory drafting，但仍然坚持 `governance-first`，不漂成 raw-retrieval support bot。

一句话定义：

`Sengent = a bounded software support agent factory`

在 `2.1` 阶段，它应当成为：

`LLM-native, but governance-first`

## Product Definition

`Sengent 2.1` 不是：

- full-RAG software copilot
- raw-doc direct runtime retrieval bot
- 让模型直接决定事实的在线知识库

它是：

- 一个利用强托管模型做理解、澄清、归纳、草拟的 software support system
- 一个仍然对当前软件负责、对版本边界负责、对知识治理负责的 support kernel
- 一个未来可承载多软件 vendor profile 的内核，而不只是 Sentieon 单点工具

## Why 2.1

`2.0` 证明了这些约束是对的：

- vendor/domain/playbook/incident layering 必须显式存在
- runtime facts 不能直接来自模型
- maintainers 必须 review，再 build / gate / activate
- clarify-first 比“尽量回答更多”更重要

但 `2.0` 运行时仍然明显受限于 local small model 假设：

- runtime/doctor/config 对 `Ollama` 有很强默认依赖
- prompt 组装和报错恢复里有大量 small-model/local-host 假设
- knowledge factory 虽然已有离线 draft 接缝，但还没有朝强托管模型的完整演进路线

`2.1` 的目的不是推翻 `2.0`，而是在不破坏治理边界的前提下，把模型层升级为 hosted-first。

## Scope

`2.1` 第一阶段只做 architecture + contract + PoC。

包含：

- hosted-LLM runtime architecture
- `OpenAI-compatible` adapter seam
- anti-drift governance principles
- provider-aware config / diagnostics / runtime wiring plan
- 明确保留哪些 `2.0` control surfaces 不动
- 独立 worktree / branch 上的实验性实现

不包含：

- raw ingestion 直接进入 runtime truth
- model outputs 直接进入 active packs
- auto-activate
- multi-tenant gateway 平台化
- 第二 vendor profile 落地
- full prompt/policy rewrite

## Non-Goals

本阶段明确不做：

- “把 docs/RAG 接得更广”来换更像人的回答
- 让 runtime 直接读 source inbox / source bundles / raw docs
- 用训练权重代替正式知识层
- 用模型推断代替 deterministic diagnostics
- 因为 hosted model 更强而弱化 review / rollback / audit

## Current State Audit

当前代码里与 `2.1` 直接相关的现状很清楚：

### 1. `llm_backends.py` 已经有 hosted adapter 雏形，但位置仍是 fallback

- `OpenAICompatibleBackend` 已存在
- `BackendRouter` 已支持 primary/fallback
- 但 `build_backend_router()` 仍把 `OllamaBackend` 固定成 primary

这意味着 hosted path 现在只是应急后备，不是正式 runtime contract。

### 2. `config.py` 仍是 Ollama-first

当前配置模型是：

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_KEEP_ALIVE`
- `SENGENT_LLM_FALLBACK_*`

这套 contract 默认假设本地小模型是主路径，hosted 只是补位。

### 3. `doctor.py` / `runtime_guidance.py` 仍是本地模型运维导向

- doctor probe 直接调用 `probe_ollama`
- guidance 默认建议 `ollama pull`
- build-only host 与 runtime host 的区分仍围绕本地模型安装状态展开

这与 `2.1` 的 hosted-first 目标不匹配。

### 4. `Support Kernel` / `Knowledge Compiler` / `Knowledge Factory` 的治理骨架是对的

这些必须保留：

- active knowledge 仍是 runtime truth source
- build / review / gate / activate / rollback
- clarify-first
- gap capture / controlled learning loop
- deterministic diagnostics
- vendor profile + domain standards + playbooks + incident memory layering

`2.1` 不应重写这些层，而应让更强模型服务于这些层。

## Hard Boundary

### 1. Runtime Never Reads Raw Ingestion As Truth

runtime 可以读取：

- active packs
- compiled vendor/domain/playbook/incident layers
- 当前会话上下文

runtime 不可以把以下内容直接当事实源：

- source inbox
- factory drafts
- raw vendor docs
- raw parsed text bundles
- hosted model outputs

### 2. Model Outputs Are Drafts, Never Truth

模型可以产出：

- answer wording
- clarification wording
- candidate drafts
- normalization drafts
- contradiction clusters
- dataset drafts

模型不可以直接产出：

- active fact mutation
- gate pass
- activated runtime truth

### 3. Hosted Runtime Must Stay Bounded By The Support Contract

更强模型不意味着更大的事实自由度。

runtime 仍必须：

- obey vendor profile boundaries
- obey version boundaries
- clarify before guessing
- cite evidence tiers rather than free-associate

### 4. Every Evolution Path Must Preserve Rollback

无论是 runtime provider 切换，还是 factory adapter 升级，都必须保留：

- config-level rollback
- pack-level rollback
- maintainer review rollback
- branch/worktree rollback

## Target 2.1 Architecture

### 1. Thin Client / CLI

继续保留 CLI-first operator surface。

它负责：

- chat / single-turn entry
- doctor / inspect / review commands
- operator-visible runtime diagnostics

它不负责：

- truth governance
- raw doc retrieval policy

### 2. Support Control Layer

这是 `2.1` 仍然最重要的 runtime layer。

它继续负责：

- intent parsing
- evidence hierarchy
- clarify-first
- answer contract
- gap capture

这里的核心变化不是“加更多规则”，而是：

- 减少为小模型补洞的机械 prompt 拼装
- 保留 contract / boundary / evidence discipline
- 把更强模型当作受控解释器，而不是事实源

### 3. Knowledge Compiler + Active Knowledge

这层保持 `2.0` 治理结构不动：

- inbox
- build
- review
- gate
- activate
- rollback

这是 `2.1` 必须保护的核心资产，而不是待替换模块。

### 4. Knowledge Factory

`2.1` 最应增强的是 factory，不是 runtime truth path。

factory 应逐步能用 stronger hosted models 产出：

- candidate facts
- candidate support boundaries
- candidate clarification triggers
- candidate playbooks
- candidate incident clusters
- dataset drafts

但这些都必须继续以 `draft + review_required` 形式存在。

### 5. Deterministic Diagnostics

diagnostics 仍是一等公民。

`2.1` 要保留并增强：

- provider reachability checks
- configured-model availability checks
- knowledge/runtime separation checks
- build/runtime host role guidance

只是 probes 不应再只围绕 `Ollama`。

### 6. OpenAI-Compatible LLM Adapter

`2.1` 的最小模型接缝应采用 `OpenAI-compatible` adapter。

原因：

- 先兼容广泛 hosted providers
- 保留将来接 gateway 的接缝
- 不在第一阶段引入复杂 provider SDK matrix

最小 canonical fields 应覆盖：

- `provider`
- `base_url`
- `api_key`
- `model`
- optional provider headers
- optional timeout / stream options

## Control Surface Decisions

### 1. Canonical Runtime LLM Config Must Become Provider-Aware

`2.1` 应把运行时配置收口为 canonical contract。

建议第一版至少引入：

- `SENGENT_RUNTIME_LLM_PROVIDER`
- `SENGENT_RUNTIME_LLM_BASE_URL`
- `SENGENT_RUNTIME_LLM_MODEL`
- `SENGENT_RUNTIME_LLM_API_KEY`
- `SENGENT_RUNTIME_LLM_KEEP_ALIVE`

其中：

- `ollama` 仍是兼容 provider
- `openai_compatible` 是 hosted-first provider

旧的 `OLLAMA_*` 与 `SENGENT_LLM_FALLBACK_*` 可以作为 compatibility aliases 暂存，但不再代表长期主 contract。

### 2. Runtime And Factory Adapter Contracts Must Stay Separate

虽然二者都可能走 `OpenAI-compatible` transport，但不能共用“truth responsibility”。

runtime adapter 用于：

- answer generation
- clarification wording
- bounded reasoning

factory adapter 用于：

- drafting
- normalization
- clustering
- dataset preparation

二者共享 transport seam，但不共享 truth semantics。

### 3. Doctor Must Become Provider-Aware

`doctor` 的职责要从：

- “本地 Ollama 好了没有”

升级为：

- “当前配置的 runtime provider 是否可达”
- “当前配置的 model 是否可用”
- “当前主机更适合 runtime 还是 build/review”
- “当前 knowledge/runtime separation 是否健康”

### 4. Runtime Guidance Must Stop Assuming Local Model Ops

`2.1` 的 guidance 不能默认建议：

- 安装 Ollama
- `ollama pull`

它应该基于 provider 输出：

- hosted credential/config guidance
- local provider guidance
- build-only host guidance

## First Implementation Slice

第一实现 chunk 必须压在最小、低风险、可验证的地方：

### Chunk A: Hosted Adapter Contract Foundation

包含：

- canonical runtime provider config
- `build_backend_router()` 改用 provider-aware primary selection
- 保留 `ollama` / `openai_compatible` 两种 provider
- backward-compatible env alias mapping
- focused tests

不包含：

- doctor / CLI 文案全面改造
- factory remote provider integration
- prompt strategy rewrite
- provider gateway

### Chunk B: Provider-Aware Doctor And Runtime Guidance

在 chunk A 稳定后，再做：

- provider-neutral doctor report shape
- provider-aware guidance text
- CLI runtime failure path 改造

### Chunk C: Hosted Factory Adapter Planning

这不是第一实现 chunk，但必须在 `2.1` 计划里预留。

届时要做的是：

- factory-side hosted adapter contract
- offline audit fields
- factory-only credential/config seam

## Success Criteria

`2.1` 第一阶段成功，不是因为系统“更像聊天机器人”，而是因为以下条件同时成立：

- runtime provider 不再被硬编码成 Ollama-first
- hosted model 可以成为正式 runtime primary path
- 2.0 control surfaces 没有被削弱
- doctor / rollback / audit 的故事更清楚，而不是更模糊
- factory 升级方向被明确保留，但没有侵入 runtime truth path

## Failure Modes To Avoid

最危险的失败不是“接不上 hosted API”，而是边界漂移。

必须避免：

- 为了更强模型而让 raw docs 直接进入 runtime truth
- 为了简化 UX 而跳过 review / gate / activate
- 把 runtime 和 factory 的 adapter 语义混为一谈
- 把“回答更像人”误解成“可以少做 governance”

一句话红线：

`Sengent may become more model-native, but it must never become raw-retrieval-native.`
