# Sengent 2.0 Support Kernel Design

## Goal

把 `Sengent` 从“Sentieon 资料问答器”升级为“面向高约束科研/工程软件的本地技术支持内核”，并以 `Sentieon` 作为第一个正式 vendor profile 落地。

这次设计的重点不是换一个更大的模型，也不是接一个更通用的 RAG 框架，而是让系统对“当前软件负责”：

- 回答时忠于该软件的官方知识、支持边界和版本边界
- 遇到证据不足时先澄清，而不是猜测
- 能把行业标准知识、排障流程和真实坏例子纳入受控知识层
- 后续可以接入 `GATK`、`LS-DYNA` 等其他软件，而不需要重做整套支持系统

## Problem

当前 `Sengent 1.x` 的方向并不错误，但产品形状还停留在“资料型支持”。

已经具备的强项包括：

- `rule-first`
- `structured-pack-first`
- 离线 `build / review / gate / activate / rollback`
- 本地运行、可审计、可回退
- 已有一定的 workflow guidance、external guides、closed-loop 评测链路

但当前版本仍然有几个明显问题：

1. 回答偏生硬，像命中资料后吐出答案，而不像资深技术支持工程师理解任务后给建议。
2. 对用户意图的理解仍偏“问题类型”，还不够偏“你现在要完成什么工作”。
3. 知识层以 `module / workflow / external-format / external-tool / external-error` 为主，还不够表达“建议、排障流程、现场经验”。
4. runtime 还没有把“证据不足就澄清”和“知识缺口回流 build pipeline”做成正式闭环。
5. 代码结构仍显著绑定 `Sentieon`，不利于未来扩展到更多软件支持。

## Product Definition

`Sengent 2.0` 的正式产品定义是：

> 一个把通用智能严格约束进软件专属责任边界里的本地技术支持内核。

其中：

- 大模型负责理解用户表达、组织回答和辅助澄清
- 软件专属知识层负责事实、建议边界和排障路径
- runtime 决策层负责判断该走哪条支持路径
- knowledge compiler 负责把原始材料编译成 runtime 真正消费的正式知识

这意味着 `Sengent 2.0` 不是：

- 通用 RAG 聊天器
- 任意发挥的 agent
- 仅对 `Sentieon` 有效的一次性实现

## Design Principles

### 1. Vendor Responsibility First

系统在做某个软件的技术支持时，必须优先对该软件负责，而不是对“行业平均做法”负责。

### 2. Evidence Before Advice

建议必须建立在正式知识和明确证据之上。证据不足时默认先澄清，不允许以“模型应该懂”作为补洞机制。

### 3. Build-Time Learning, Runtime Determinism

学习发生在离线知识层，而不是运行时偷偷改“脑子”。

runtime 只消费：

- 已通过 review/gate 的正式知识
- 当前会话中明确提供的上下文信息

### 4. Domain Standards Are First-Class

成熟的软件技术支持不能只靠 vendor 文档。

对于生信软件，`VCF/BAM/CRAM/BED/FASTA/索引/字典/header/坐标语义` 这类行业标准知识必须成为一等公民，而不是仅作为补丁式外部资料存在。

### 5. Kernel / Vendor Separation

系统必须从结构上区分：

- 可复用的 support kernel
- 可替换的 vendor profile

这样未来新增软件时，新增的是 profile、packs 和 eval corpus，而不是重写整个系统。

## Scope

本设计覆盖：

- `Sengent 2.0` 的总体分层架构
- knowledge taxonomy 升级
- runtime decision model
- answer contract
- gap capture / controlled learning loop
- repo 和文档层面对未来新增软件的扩展接口

本设计不覆盖：

- 具体 UI 改版
- 跨机器分布式编排
- 训练模型权重
- 第二个软件 profile 的正式落地实现

## System Architecture

`Sengent 2.0` 由四层组成。

### 1. Support Kernel

这层是软件无关、未来所有软件实例共享的内核。

职责：

- support intent 识别
- evidence hierarchy
- clarify policy
- answer contract enforcement
- gap capture
- operator-facing workflow contract

这层不应出现 `sentieon`、`gatk`、`ls-dyna` 等软件名耦合。

### 2. Knowledge Compiler

这层保留当前 `1.x` 已经验证过的主思路：

- ingest raw sources
- normalize / canonicalize
- compile candidate packs
- review artifacts
- eval gate
- activate / rollback

但其输出知识类型需要升级，不再只围绕 `module / workflow / external-*`。

### 3. Runtime Decision Engine

这层负责把“用户说了什么”转换成“当前应该走哪条支持路径”。

它不是简单的检索路由，而是要判断：

- 用户是在理解概念、请求建议、排查故障，还是确认下一步动作
- 当前证据够不够
- 应该优先走 vendor knowledge、domain standards、playbook 还是 incident memory
- 什么时候必须先澄清

### 4. Vendor Profile Layer

这层定义某个具体软件实例的支持边界。

一个 vendor profile 至少包含：

- 软件标识与版本体系
- 官方知识入口
- 领域标准依赖
- 支持边界
- 默认澄清策略
- eval corpus

`Sentieon` 是第一个正式 vendor profile。

## Knowledge Taxonomy

`Sengent 2.0` 不再把 active knowledge 仅看成“参考资料包”，而是升级成六类正式 pack。

### 1. `vendor-reference`

用于描述软件本身的事实型知识：

- 模块/命令/参数
- 输入输出
- 官方术语
- 版本可追溯事实

### 2. `vendor-decision`

用于描述“在该软件语境下应该怎么选”的判断规则：

- 某类场景推荐走哪条 workflow
- 哪些路径可做、但不推荐
- 何时必须补齐信息再继续
- 哪些结论只能在特定版本成立

### 3. `domain-standard`

用于描述与该软件强相关的行业标准知识：

- 文件格式语义
- 兼容性约束
- 索引/字典/header/坐标规则
- 外部生态工具常见行为

### 4. `playbook`

用于描述操作型支持路径：

- 排障流程
- 修复步骤
- 验证步骤
- rollback / retry 策略

### 5. `troubleshooting`

用于描述高频已知问题：

- 症状
- 常见根因
- 区分方式
- 推荐下一步

### 6. `incident-memory`

用于描述从真实现场闭环中学到的经验：

- 坏例子
- 误判模式
- 客户环境约束
- 需要重新评测的风险点

这些 pack 都必须经过 build/review/gate/activate，不能直接绕过正式链路进入 runtime。

## Evidence Hierarchy

runtime 在生成建议时遵守如下证据优先级：

1. 当前 vendor profile 的正式 active packs
2. 该 profile 依赖的 domain-standard packs
3. 当前 profile 的 playbook / troubleshooting / incident-memory
4. 当前会话中用户明确补充的上下文信息

下面几类内容不能直接提升为正式结论：

- 模型凭常识的自由推断
- 未入库的零散网页内容
- 与当前软件支持边界无关的泛行业建议

如果正式证据不足，默认策略是：

1. 明确说明不确定
2. 说明缺什么材料
3. 给出下一步澄清问题

而不是给一个高自信猜测答案。

## Support Intents

`Sengent 2.0` 的 runtime 不再只停留在 `reference / troubleshooting / onboarding`，而升级成更贴近技术支持工作的 intent 集合：

- `concept-understanding`
- `task-guidance`
- `decision-support`
- `troubleshooting`
- `validation-next-step`
- `knowledge-gap`

其中最关键的是：

- `decision-support`
- `troubleshooting`
- `knowledge-gap`

这三类 intent 决定系统是否开始像资深技术支持工程师工作，而不是只像资料索引器。

## Runtime Decision Flow

推荐的 2.0 runtime 决策顺序如下：

1. 识别当前 vendor profile
2. 识别 support intent
3. 提取显式上下文槽位
4. 判断证据是否足够
5. 如果不足，优先进入 clarify / knowledge-gap
6. 如果足够，按 evidence hierarchy 选择知识层
7. 按对应 answer contract 生成最终回答

系统不应先检索再决定“这是什么问题”，而应先判断用户想完成什么，再决定如何检索和回答。

### Clarify And Fallback Rules

`Sengent 2.0` 的澄清路径必须显式定义失败分支，而不是默认无限追问。

默认最大澄清轮次固定为 `2`。超过这个次数后，不再进入新的 `clarification-open`。

#### Case 1: 证据不足但可明确补齐

输出：

- 当前缺什么信息
- 为什么缺它
- 下一轮应该补什么

并把当前 turn 标记为 `knowledge-gap-candidate` 或 `clarification-open`。

#### Case 2: 连续澄清后仍不足

如果同一问题已经过默认最大澄清轮次，仍无法形成正式结论：

- 不再继续循环追问
- 输出保守边界答案
- 明确说明当前无法确定的原因
- 提示应转为资料补充或人工升级处理

#### Case 3: 证据冲突

如果 vendor pack、domain-standard 或 incident-memory 之间存在冲突：

- 明确指出冲突存在
- 优先遵守 vendor-support boundary
- 不把冲突强行压成一个确定性建议
- 把该 turn 标记为 `conflict-review-candidate`

#### Case 4: 无答案路径

如果既没有足够证据、也没有明确澄清槽位、也不属于当前支持边界：

- 输出 `no-answer-with-boundary`
- 说明为什么当前系统不应该给结论
- 指向需要补充的材料类型或人工升级路径

### Fallback Precedence

当多个 fallback 条件同时成立时，runtime 必须遵守这个优先级：

1. `unsupported-version`
2. `conflicting-evidence`
3. `clarification-open`（仅当未超过 2 轮）
4. `no-answer-with-boundary`

### Canonical Boundary Output Shape

所有 boundary / no-answer 响应必须至少包含：

- `reason`
- `why_not_deterministic`
- `needed_materials_or_next_action`
- `current_scope_boundary`

## Answer Contracts

不同类型的问题必须使用不同的回答 contract。

### A. 概念/参考类

至少包含：

- 这是什么
- 适用范围
- 与当前软件相关的边界
- 来源

### B. 建议/决策类

至少包含：

- 当前推荐结论
- 适用前提
- 不推荐的相邻路径
- 风险或不确定点
- 建议如何验证
- 来源

### C. 排障类

至少包含：

- 当前最可能的问题判断
- 证据依据
- 下一步排查动作
- 需要补充的信息
- 如果失败如何回退或继续分流
- 来源

### D. 知识缺口类

至少包含：

- 当前不能确定的原因
- 需要补充的材料类型
- 为什么这些材料是必要的
- 材料进入系统后的下一步

## Controlled Learning Loop

`Sengent 2.0` 需要一个受控学习闭环，但不是在线训练模型。

推荐流程：

1. runtime 识别知识缺口
2. 明确告诉用户缺什么材料
3. 把材料收进 knowledge inbox
4. 通过 build / review / gate / activate 编译进正式知识
5. 用 eval/closed-loop 验证新能力
6. 下次同类问题命中新知识

这条链路的核心是：

- 学到的是正式知识，不是 prompt 偶然记忆
- 每次学习都必须留下可审计痕迹
- 每次学习都应该有对应的 eval case 或 incident case

### Gap Record Contract

为了让 runtime 缺口真正回流 build pipeline，系统需要一个最小 gap record：

- `vendor_id`
- `vendor_version`
- `intent`
- `gap_type`
- `user_question`
- `known_context`
- `missing_materials`
- `captured_at`
- `status`

其中 `gap_type` 至少区分：

- `missing_vendor_reference`
- `missing_vendor_decision`
- `missing_domain_standard`
- `missing_playbook`
- `conflicting_evidence`
- `unsupported_version`

这保证 gap capture 不是一句文本提示，而是后续 review/build 可以真正消费的正式输入。

## Repository And Extensibility Model

2.0 从第一天就要为多软件扩展留接口。

推荐逻辑结构如下：

- `src/sentieon_assist/` 中保留软件无关 support kernel 与 compiler 核心
- 新增独立的 vendor/profile 层目录，用于存放每个软件的 profile、templates、eval 和 pack defaults

推荐的概念结构：

- `src/sentieon_assist/kernel/...`
- `src/sentieon_assist/vendors/sentieon/...`
- 未来扩展为 `src/sentieon_assist/vendors/<vendor>/...`

### Minimal Vendor Profile Contract

每个 vendor profile 必须至少定义以下接口：

- `vendor_id`
- `display_name`
- `default_version`
- `supported_versions`
- `pack_manifest`
- `domain_dependencies`
- `clarification_policy`
- `support_boundaries`

其中：

- `vendor_id` 是 runtime 选择 profile 的稳定键
- `default_version` 用于用户未显式给版本时的默认资料族
- `supported_versions` 用于判断当前版本是否受支持
- `pack_manifest` 定义这个 vendor 运行时必须加载哪些 pack
- `domain_dependencies` 定义该 vendor 依赖的行业标准 pack
- `clarification_policy` 定义默认追问槽位和最大澄清轮次
- `support_boundaries` 定义该 vendor 当前不允许给出确定性建议的主题边界

### Pack Manifest Contract

每个 vendor profile 的 `pack_manifest` 必须至少显式列出：

- `vendor-reference`
- `vendor-decision`
- `domain-standard`
- `playbook`
- `troubleshooting`
- `incident-memory`

manifest 中的每类 pack 需要声明：

- `required: true|false`
- `file_name`
- `entry_schema_version`
- `load_order`

这样 kernel 可以独立于具体 vendor 进行 pack 完整性检查，而 vendor profile 只负责声明自己的资料契约。

### Runtime Vendor Resolution Contract

runtime 在进入回答之前，必须完成 vendor / version 选择：

1. 如果 CLI 或调用方已显式指定 vendor/profile，直接使用该 profile
2. 如果当前实例只有一个激活 profile，可使用它作为默认 profile
3. 如果用户问题显式带版本，则优先选择该版本对应资料族
4. 如果用户未给版本，则选择 profile 的 `default_version`
5. 如果版本不受支持，系统不进入猜测式回答，而进入 `unsupported-version` clarify / boundary 路径

这保证 kernel 可以独立工作，而 vendor-specific 数据只通过 profile contract 注入。

### Runtime Profile Loading Contract

runtime 选择到某个 vendor profile 之后，必须按统一方式装载资料：

1. profile 定义本身是代码内 source of truth，位于 `src/sentieon_assist/vendors/<vendor>/profile.py`
2. active runtime packs 的 source of truth 位于当前 `source_directory`
3. runtime 通过 profile 的 `pack_manifest` 把逻辑 pack kinds 映射到物理文件
4. 每个 pack 文件必须先过 schema validation，才允许进入 runtime
5. 缺少 `required: true` 的 pack 时，profile 被视为 `runtime-incomplete`
6. `runtime-incomplete` 不允许静默降级成“模型随便答”，而进入 boundary / operator guidance 路径

### Missing / Partial Pack Rules

- 缺少 required pack：
  - `doctor` 标记 profile 不完整
  - runtime 对相关问题输出保守边界答案，不给确定性建议
- 缺少 optional pack：
  - 允许继续，但对应能力应显式退化
- pack 文件存在但 schema 非法：
  - 视为 invalid pack，不参与 runtime
  - 进入 review/gate 问题，而不是让模型兜底

### Explicit Vendor / Version Conflict Rules

如果输入同时显式给了 vendor/profile 和 version：

1. 显式 vendor/profile 优先决定要加载哪个 profile
2. version 只在该 profile 内部解析
3. 如果该 version 不在该 profile 的 `supported_versions` 内：
   - 不切换到别的 profile
   - 不模糊回退到默认 version
   - 直接进入 `unsupported-version` 边界路径

同时需要新增两类指导文档：

1. `platform principles`
   - 定义 kernel 的职责、证据优先级、澄清策略和学习闭环

2. `vendor onboarding contract`
   - 定义接入一个新软件时必须准备什么：
     - 官方资料
     - domain standards
     - playbooks
     - bad cases / incident cases
     - eval corpus
     - 支持边界

这保证 2.0 不是写死在 `Sentieon` 上的单实例实现。

## Migration Strategy

建议采用并行的 `2.0 kernel` 策略，而不是在 `1.x` 原地硬拧。

### 保留复用的 1.x 资产

- app paths / packaging / install UX
- backend router
- doctor
- knowledge build 主流程
- pilot readiness / closed loop gates
- activate / rollback

### 需要在 2.0 重构的核心层

- support intents
- knowledge taxonomy
- runtime decision layer
- answer contracts
- gap capture / controlled learning loop
- vendor / domain / playbook / incident 的正式分层

## Phase 1 Recommendation

为了尽快把产品从“资料助手”推向“支持助手”，第一阶段拆成四个有依赖顺序的 milestone。

### Milestone 1: Kernel And Profile Contracts

交付：

- `platform principles`
- `vendor onboarding contract`
- vendor profile 接口
- pack manifest 契约

退出条件：

- kernel 不再硬编码 vendor-specific 结构假设
- `Sentieon` profile 可以通过正式 contract 被 runtime 加载
- `python3.11 -m pytest -q tests/test_pack_contract.py tests/test_vendor_profiles.py tests/test_docs_contract.py` 通过

### Milestone 2: Knowledge Taxonomy Upgrade

交付：

- 六类 pack 的 schema/manifest
- build / doctor / activate / rollback 对新 taxonomy 的契约支持
- 必要的兼容层或迁移层

退出条件：

- candidate build 能生成或验证 2.0 taxonomy
- managed pack 完整性检查不再只绑定 1.x 文件集合
- `python3.11 -m pytest -q tests/test_knowledge_build.py tests/test_doctor.py` 中与 managed packs / taxonomy 相关的新增用例通过

### Milestone 3: Runtime Decision And Answer Contracts

交付：

- 新 support intents
- clarify/fallback rules
- 建议类 / 排障类 / knowledge-gap 类 answer contracts

退出条件：

- runtime 能明确区分参考、建议、排障和 knowledge-gap
- 证据不足时默认进入 clarify / boundary，而不是猜测
- 至少存在这些可评测分支的自动化用例并通过：
  - supported version
  - unsupported version
  - conflicting evidence
  - unresolved knowledge gap

### Milestone 4: Controlled Learning Loop

交付：

- 最小 gap record
- runtime gap capture
- review/build 可见的 gap intake 接口
- `Sentieon` 首轮闭环验证

退出条件：

- 同类缺口可以被正式记录、回流、编译并验证
- `Sentieon` 作为首个 vendor profile 完成 2.0 第一圈闭环
- `gap record -> review/build intake -> eval case` 至少有一条端到端样例通过

## Success Criteria

2.0 第一阶段完成后，应至少满足：

1. 系统可以明确区分参考问答、建议、排障和知识缺口。
2. 对证据不足的问题，默认先澄清而不是猜测。
3. active knowledge 可以表达 vendor facts 之外的 decision/playbook/troubleshooting/incident。
4. repo 结构和原则文档已经为未来新增软件留出明确接口。
5. 对 `Sentieon` 的首轮实现仍保留离线 build、gate、activate/rollback 的可控性。

## Why This Design Fits The Current Project

当前项目最宝贵的部分不是现有 `Sentieon` 特化命名，而是已经被验证过的这些原则：

- 本地优先
- rule-first
- structured-pack-first
- eval-gated
- activation reversible

`Sengent 2.0` 的正确方向不是推翻它们，而是把它们从 `Sentieon` 的一次性实现，提升成一个真正可复用的软件支持内核。
