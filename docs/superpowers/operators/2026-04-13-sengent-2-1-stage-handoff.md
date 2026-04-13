# Sengent 2.1 阶段性状态与交接摘要

这份文档用于把 `Sengent 2.1` 当前阶段的事实状态、设计边界、完成情况和剩余口子一次性落盘，供主线程、维护者和后续测试直接复用。

## 当前定位

`Sengent 2.1` 现在处在：

- `hosted-runtime internal branch`
- `governance-first PoC completed`
- `pre-human-test gated`

它不是 release 版，也不是 customer-ready 产品，更不是 full RAG support bot。

当前版本的核心定位仍然是：

- `LLM-native, but governance-first`
- `Sengent = a bounded software support agent factory`
- runtime 可以更轻，但不能靠放弃知识治理来变轻
- factory 可以更依赖 hosted GPT 做草拟，但模型输出仍然只是 `draft`, not truth

## 架构设计已经固定下来的部分

`2.1` 不是推翻 `2.0`，而是在保留治理内核的前提下，把 runtime 和 factory 分别接到 hosted model seam。

当前已经固定的架构边界：

- 保留 `vendor / domain / playbook / incident` knowledge layering
- 保留 `build / review / gate / activate / rollback`
- 保留 `clarify-first`
- 保留 deterministic diagnostics
- runtime never reads raw ingestion directly as truth
- model output is `draft only unless promoted`
- tool-required intents cannot fall回 model-only reasoning
- factory hosted learning stays `offline + review-only`
- no auto-activate
- no direct mutation of active packs from model output

`2.1` 当前实际分层可以理解成：

- Thin Client / CLI
- Support Control Layer
- Boundary Pack + Active Knowledge
- Tool Arbitration Layer
- Deterministic Diagnostics
- Capability-Based LLM Adapter
- Knowledge Factory
- Eval / Trace Plane
- Trust Boundary Layer

## 已完成的主线工作

### 1. Hosted runtime 基础面

已完成：

- canonical runtime provider contract
- capability-based provider descriptor
- provider-neutral outbound request seam
- provider-aware doctor / runtime guidance / CLI wiring
- hosted runtime outbound trust boundary
- chat polish trust boundary hardening

结果：

- runtime 已可走 `openai_compatible`
- 但 runtime 仍然受 active knowledge、boundary pack、tool arbitration 约束
- hosted path 没有把系统漂成 raw retrieval runtime

### 2. Governance 核心约束

已完成：

- anti-drift invariants code surface
- trust boundary result + summary persistence
- outbound audit trail review surfaces
- sanitized outbound request path
- eval / trace plane 基础接线

结果：

- hosted prompt 出站前会经过 trust-boundary 约束
- session / review / dataset export 已能看到 boundary summary
- 审计面至少达到了 pre-human-test 所需的 maintainer 可见性

### 3. Tool arbitration 与 boundary pack

已完成：

- explicit boundary pack surface
- explicit tool arbitration surface
- support / reference / reference-intent caller integration

结果：

- 文件结构、格式一致性、header/index/contig/sort 这类问题不会再被当成“模型自由解释题”
- `must-tool`、`must-clarify`、`must-refuse` 已进入统一 contract

### 4. Hosted factory 与行业知识学习试点

已完成：

- separate factory hosted config surface
- factory hosted adapter seam
- factory outbound trust boundary
- hosted factory learning pilot
- learning provenance aggregation into review/eval/export

结果：

- hosted GPT 已可用于 factory draft / industry-knowledge learning pilot
- 但 factory 仍严格停留在 `review_needed`
- learning output 会进入 maintainer review，而不是进入 runtime truth path

### 5. Pre-human-test gate

已完成：

- operator gate doc
- docs contract coverage
- focused verification gate
- fresh full regression

当前 gate 结果：

- docs contract: passed
- focused gate: passed
- full suite: `649 passed`
- live smoke: not run yet because explicit runtime/factory provider config is not present in the current environment

## 当前完成度判断

如果按 `2.1 hosted-LLM + governance-first` 的首轮目标来看，当前状态是：

- `architecture intent`: complete
- `post-PoC hardening roadmap`: complete
- `runtime hosted path`: complete for internal testing
- `factory hosted learning pilot`: complete for offline review-only testing
- `pre-human-test documentation and regression gate`: complete
- `live provider smoke`: pending
- `structured human testing`: ready after provider config is supplied

换句话说，当前还没完成的不是架构主线，而是测试入口条件。

## 当前还没收口的部分

这些不阻止进入人工测试前准备，但它们仍然是明确的剩余口子：

### 1. Live provider smoke

当前环境没有明确的：

- `SENGENT_RUNTIME_LLM_*`
- `SENGENT_FACTORY_HOSTED_*`

所以还没正式完成：

- `sengent doctor`
- `sengent chat`
- `sengent knowledge factory-draft --help`

在真实 provider 配置下的一轮 live smoke。

### 2. Customer-facing packaging

当前仍然没有做：

- release packaging
- customer install packaging
- gateway / multi-tenant rollout
- public release promise

这仍然只是 internal branch。

### 3. Factory learning 扩张面

当前只完成了 bounded pilot，没有完成：

- 大规模 contradiction clustering
- richer dataset authoring automation
- multi-vendor knowledge learning

这些是后续增强层，不是当前 pre-human-test gate 的缺口。

## 当前最重要的结论

现在不能把 `2.1` 描述成：

- full RAG support bot
- GPT 直接学完就变成知识库
- runtime 直接信 raw docs
- customer-ready hosted support product

现在可以准确描述成：

- 一个已经完成 governance-first hardening 的 `hosted runtime + hosted factory internal branch`
- runtime 仍然以 active knowledge 为 truth
- hosted GPT 已接入 runtime 和 factory，但都被明确边界治理约束
- branch 现在缺的是真实 provider config 下的 live smoke，而不是新的核心架构改写

## 当前分支与基线

当前工作分支：

- `codex/sengent-2.1`

关键阶段提交：

1. `1b99189 docs: add 2.1 post-poc hardening roadmap`
2. `ba33b3a refactor: harden hosted runtime provider seam`
3. `5d2a72a feat: add outbound audit trail review surfaces`
4. `dfa1b7b feat: add hosted factory adapter seam`
5. `6a0555e feat: add hosted factory learning pilot`
6. `7178246 docs: add 2.1 pre-human-test gate`

本次阶段总结提交之后，这份文档将作为新的 handoff 落点。

## 进入下一步前的最小动作

如果要继续往前，不需要再先改架构。先做这几件事：

1. 配 runtime hosted provider env/config
2. 配 factory hosted provider env/config
3. 跑 live smoke：`doctor` / `chat` / `knowledge factory-draft --help`
4. 基于这轮 smoke 结果进入 structured human testing

一句话结论：

`Sengent 2.1` 的治理内核和 hosted 分层已经阶段性收口；下一步不是再发明新架构，而是把真实 provider 配置接上并进入人工测试。
