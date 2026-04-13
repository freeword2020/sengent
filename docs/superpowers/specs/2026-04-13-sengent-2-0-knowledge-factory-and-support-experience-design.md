# Sengent 2.0 Knowledge Factory And Support Experience Design

## Goal

在 `Sengent 2.0` 已有 `support kernel + knowledge compiler` 基础上，正式补齐：

- `Knowledge Factory` 这条离线知识生产线
- `maintainer` 侧的低负担维护体验
- `front-end user` 侧的高获得感支持体验

并把 `Sentieon` 作为第一个落地应用，把流程跑通、维护成本压低、回答体验做厚，而不是继续停留在“能答一些资料问题”的层级。

## Why This Design Exists

当前 2.0 主骨架方向已经正确：

- runtime 不做 RAG-first
- 模型不直接主导事实判断
- `build / review / gate / activate / rollback`
- `gap capture -> inbox -> review`

但如果只停在这里，系统仍然会有三个瓶颈：

1. `知识建设成本过高`
   维护者仍然容易变成手工拆文档、手工录知识的人。

2. `支持体验仍然偏硬`
   即使 runtime 更稳了，如果前端只给出一段平铺文本，用户仍然会觉得“笨”“不够像资深工程师”。

3. `扩展到更多软件的路径还不够清晰`
   没有 Knowledge Factory，这套系统很难从 `Sentieon` 走向更多软件支持。

所以这次设计不是推翻 2.0，而是给 2.0 补上“怎么持续变强、怎么更易维护、怎么让用户明显感知到价值”的正式架构层。

## Product Definition

`Sengent 2.0` 的完整产品定义更新为：

> 一个把通用智能严格约束进软件专属责任边界里的本地技术支持平台。

这里的“平台”不是指一开始就做所有软件，而是指：

- 内核是可复用的
- 知识生产线是可扩展的
- 体验层是可迁移的
- `Sentieon` 是第一个 vendor application

## Design Priorities

### 1. Convenience First For Maintainers

维护者应该更像 `technical owner`，而不是人工录入员。

目标体验应该接近：

1. 投资料
2. 看候选
3. 审核
4. 激活

而不是：

1. 手工找资料
2. 手工拆结构
3. 手工写知识条目
4. 手工组织训练集

### 2. Runtime Must Stay Small And Stable

runtime 只能负责：

- 理解当前问题
- 命中正式知识
- 在证据边界内做支持决策
- 缺证据时澄清
- 记录 gap

runtime 不负责：

- 抓资料
- 批量抽取候选知识
- 自动训练
- 直接把新知识变成 active behavior

### 3. Knowledge Growth Must Be Offline And Controlled

新知识、经验、行业标准、训练数据都必须先走离线生产线。

任何自动化能力都只能产出：

- inbox artifacts
- review artifacts
- candidate packs
- eval seeds
- training datasets

不能直接跳过 review/gate 进入 active runtime。

### 4. User Experience Must Show Competence

前端不能只做“把答案打印出来”。

用户真正感知到的价值来自：

- 是否理解他当前想完成什么
- 是否说清楚“为什么这么建议”
- 是否明确给出下一步
- 是否在不确定时表现得克制而专业

所以体验层必须围绕 `support answer contract` 来设计，而不是围绕一段自由文本。

## System Architecture

`Sengent 2.0` 的完整分层正式定义为五层。

### 1. Support Kernel

这是运行时最小内核。

职责：

- support intent 判断
- evidence hierarchy 执行
- clarify-first 策略
- answer contract enforcement
- gap capture
- vendor boundary enforcement

输出：

- 受约束的支持回答
- 可审计 trace
- `gap_record`

约束：

- 只消费 active knowledge
- 不直接修改知识
- 不直接依赖抓取器、训练器、资料导入器

### 2. Knowledge Compiler

这是正式知识编译链。

职责：

- inbox 接收
- canonicalization
- candidate pack compilation
- review artifact generation
- gate preparation
- activate / rollback

输出：

- candidate packs
- review artifacts
- gate inputs
- active packs

约束：

- 所有可生效知识都必须经过这一层
- 任何自动抽取结果都只能作为 candidate，而不是直接 active

### 3. Knowledge Factory

这是新增的离线知识生产线。

职责：

- 官方资料导入
- 行业标准资料导入
- release notes / support case / runtime gaps 导入
- candidate extraction
- contradiction scan
- review queue generation
- eval seeding
- training dataset export

输出：

- inbox-ready artifacts
- review suggestions
- eval seeds
- training samples

约束：

- 不直接影响 runtime
- 不直接跳过 compiler
- 可以调用更大的模型，但只能作为 `factory worker`，不能替代正式知识层

### 4. Maintainer Experience Layer

这是给维护者用的操作面。

目标不是做复杂后台，而是让维护流程低负担、可连续操作。

核心能力：

- source intake
- candidate queue
- build/review visibility
- triage decision writing
- eval/gate status
- activate / rollback guidance

最低要求：

- CLI 仍然可完整操作
- 后续可叠加轻量维护界面

### 5. User Support Experience Layer

这是给最终用户的支持界面。

核心目标：

- 让用户觉得系统像一个克制、专业、理解任务的资深支持工程师
- 明显降低“回答生硬、答非所问”的体感

最低要求：

- 回答以 structured answer card 展示
- 明确显示结论、证据、边界、下一步
- gap 场景直接提供补充材料入口

## Knowledge Factory Contract

Knowledge Factory 不是一个“巨型自动化系统”，而是一条有清晰入口和出口的受控生产线。

### Inputs

- vendor official docs
- domain standards
- release notes
- maintainer-authored notes
- runtime gap intake artifacts
- support incidents

### Outputs

- scaffolded inbox entries
- candidate pack suggestions
- contradiction findings
- review queue items
- eval seeds
- training dataset exports

### Hard Boundary

Factory 输出不能直接成为 runtime facts。

必须遵循：

`Factory output -> inbox/build/review/gate -> active knowledge`

## Training Strategy

### What Training Is For

训练不是用来保存事实本身，而是用来增强 support behavior。

推荐训练目标：

- 更稳的意图理解
- 更好的澄清问题策略
- 更强的建议组织能力
- 更一致的 answer contract 遵循
- 更稳定地区分 vendor issue / domain-standard issue / env issue

### What Training Is Not For

训练不应该取代：

- vendor facts
- version boundaries
- domain-standard canonical truth
- playbook / troubleshooting / incident memory

这些都应该继续存放在正式知识层，而不是只藏在模型权重里。

### Training Asset Flow

推荐流程：

1. 正式知识和审核后的支持轨迹进入 dataset export
2. 生成高质量 SFT / LoRA 训练样本
3. 训练后的模型作为 support behavior adapter 使用
4. runtime 仍然以正式知识为事实源

### Future Large-Model Interface

未来可以增加更大的模型接口，但位置只能在 `Knowledge Factory`：

- 帮忙抽候选知识
- 帮忙整理 incident
- 帮忙生成训练样本草稿
- 帮忙做 contradiction scan

不能让它直接替代 runtime 主事实链。

## Maintainer Experience Principles

### 1. One-Way Simplicity

维护者不应该被迫理解内部所有结构。

系统应该默认提供：

- 明确的 source intake 命令
- 可审核的候选列表
- 可执行的下一步提示

### 2. Review Over Authoring

优先让维护者审核候选，而不是从零撰写结构化知识。

### 3. Build Artifacts Must Be Actionable

`knowledge review` 看到的内容必须能直接指导下一步动作，而不是只展示技术细节。

### 4. Every Gap Must Have A Home

runtime 捕获到的 gap，必须最终能落到：

- 待补资料
- 待评测
- 待拒绝/关闭

而不是长久停留在 thread 里。

## User Experience Principles

### 1. Answers Must Feel Directed

回答不是“贴一段资料”，而是“在当前场景下给出清楚判断”。

### 2. Visible Evidence Builds Trust

用户应该看到：

- 当前判断
- 证据来源
- 适用条件
- 风险
- 下一步动作

### 3. Clarify With Purpose

当证据不足时，不是简单说“信息不够”，而是要告诉用户：

- 缺什么
- 为什么缺
- 补完后系统会如何推进

### 4. Distinguish User And Maintainer Paths

用户界面面向支持解决；维护界面面向能力建设。两者不能混成一个入口。

## Sentieon As The First Application

这套设计先只服务 `Sentieon`。

原因：

- 当前知识和流程基础最完整
- 生信场景天然需要 `vendor knowledge + domain standards`
- 真实 support case 更容易暴露 Knowledge Factory 的价值

`Sentieon` 首轮跑通后，才考虑抽象成其他软件支持模板。

## Phase Ordering

推荐顺序如下：

1. 完成 Phase 5：`gap triage + eval seeding`
2. 引入 Knowledge Factory 的最小 source intake 接口
3. 强化 maintainer convenience
4. 强化 front-end support UX
5. 再考虑训练与大模型 factory interface

## Non-Goals

本设计当前不覆盖：

- 多软件同时并行接入
- 分布式抓取/编排
- 在线训练
- 自动激活知识
- 全栈后台系统一次性成型

## Success Criteria

当这条设计跑通时，应至少满足：

1. `Sentieon` 的维护者可以主要通过审核候选而不是手工录入来维护知识。
2. runtime gap 可以稳定进入 triage / eval / review 闭环。
3. 前端回答更像“资深技术支持工程师的建议”，而不是资料拼贴。
4. 更大的模型即使被接入，也只在 Knowledge Factory 中工作，而不是直接控制 runtime facts。
5. 新增第二个软件时，主要增加的是 profile、packs、factory adapters 和 eval corpus，而不是重写 kernel。

## Why This Fits The Current Project

这个设计延续并强化了当前项目最宝贵的原则：

- local-first
- rule-first
- structured-pack-first
- eval-gated
- reversible activation

它做的不是把 `Sengent` 变成一个更花哨的聊天器，而是把现有正确方向正式提升成：

- 可持续变强
- 可低负担维护
- 可被用户明显感知价值
- 可扩展到其他软件支持

的平台级支持系统。
