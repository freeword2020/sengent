# Sengent 2.0 Factory Model Interface Design

## Goal

给 `Knowledge Factory` 增加第一个正式的大模型接口层，但严格限定在 offline / factory 场景里。

这个接口的目标不是把模型接进 runtime，而是让 factory worker 可以在受控边界内做：

- candidate drafting
- incident normalization
- contradiction clustering
- dataset drafting

同时保留完整审计链。

## Scope

本阶段只做 `large-model factory interface` 的第一个完整 chunk。

包含：

- provider-agnostic factory model interface contract
- offline draft artifact contract
- stub/local adapter
- CLI-first operator surface
- auditability fields

不包含：

- 真实远程模型接入
- runtime 直接调用模型
- active pack 自动修改
- 自动 activate
- 编译链路内自动接受模型产物

## Problem

前面几个子阶段已经把 `Knowledge Factory` 的入口、maintainer queue、support UX、dataset export 都补齐了，但“未来更大模型只能放在 factory 层”这个边界还没有正式落成代码接口。

如果没有这一层，后续一旦引入更大模型，很容易出现两类问题：

### 1. Boundary Drift

模型能力会直接侵入：

- runtime answering
- active pack mutation
- maintainer review shortcut

这会破坏 2.0 的核心原则。

### 2. Auditability Loss

如果只是“调一下模型拿点结果”，后续维护者很难回答：

- 这个 draft 是哪个 prompt 生成的？
- 参考了哪些 source？
- 是哪个 adapter 产出的？
- 为什么它仍然需要 review？

所以必须先把接口层和 artifact contract 定清楚，再谈更强的 model worker。

## Hard Boundary

### 1. Factory Model Workers Are Offline Only

允许：

- candidate drafting
- incident normalization
- contradiction clustering
- dataset drafting

不允许：

- direct runtime answering
- automatic fact override
- direct active-pack mutation
- bypass build / review / gate / activate

### 2. Model Output Is Draft, Never Truth

任何 factory model 产物都只能是：

- `draft artifact`
- `review_needed`
- `candidate for maintainer review`

不能直接成为：

- active knowledge
- runtime facts
- gate pass 依据

### 3. Interface Must Be Provider-Agnostic

第一版即使只有 stub adapter，也要把接口抽象成以后能接：

- local adapters
- OpenAI-compatible adapters
- 其他离线 worker

但这些未来 adapter 也必须受同一审计 contract 约束。

## First Implementation Slice

这次只做最小闭环：

1. offline draft artifact contract
2. provider-agnostic adapter protocol
3. stub adapter
4. CLI `knowledge factory-draft`

这次不做：

- remote provider calls
- model router reuse for factory
- automatic inbox materialization
- task-specific deep parsing

## Supported Factory Tasks

第一版先把允许的 task kind 固化下来。

### 1. `candidate_draft`

用于：

- 从 source material 起草 candidate review notes

### 2. `incident_normalization`

用于：

- 把 support incident / gap material 归一化成 review 草稿

### 3. `contradiction_cluster`

用于：

- 聚类潜在矛盾候选，供 maintainer review

### 4. `dataset_draft`

用于：

- 根据 audited dataset/source refs 起草训练资产说明或草稿

## Factory Draft Request Contract

每次调用 factory model worker 时，至少要明确：

- `task_kind`
- `vendor_id`
- `adapter_id`
- `instruction`
- `source_references`
- `output_path`

其中 `source_references` 是本次 draft 的硬边界。

模型 worker 不能声称看过不在 source references 里的内容。

## Prompt / Template Provenance

每个 draft artifact 必须保存：

- `template_id`
- `template_version`
- `rendered_prompt`
- `instruction`

这样 maintainer 后续才能判断：

- 是模板本身有问题
- 还是 source refs 不够
- 还是 adapter 行为不可靠

## Source Reference Contract

每个 source reference 至少包含：

- `path`
- `label`
- `file_type`
- `preview`

这些信息既用于 prompt 组装，也用于审计追踪。

## Factory Draft Artifact Contract

第一版用单个 JSON artifact 表达。

每个 artifact 至少包含：

### 1. Identity

- `draft_id`
- `task_kind`
- `vendor_id`
- `created_at`

### 2. Adapter Provenance

- `adapter_id`
- `provider`
- `model_name`

### 3. Review Status

- `review_status`
- `review_required`

默认必须是：

- `review_status=needs_review`
- `review_required=true`

### 4. Prompt Provenance

- `template_id`
- `template_version`
- `rendered_prompt`
- `instruction`

### 5. Source References

- `source_references`

### 6. Draft Payload

- `summary`
- `draft_items`
- `review_hints`

这里的 payload 仍然只是 draft，不是 schema-validated runtime fact。

## Stub Adapter Behavior

stub adapter 的角色不是“伪装成真实模型”，而是：

- 固化接口
- 固化 artifact 结构
- 验证 CLI 和 operator flow

所以它的输出必须：

- deterministic
- review-needed
- 明确标记自己是 stub/local adapter

不能让人误以为它是已接入的真实模型。

## CLI Contract

建议入口：

```bash
sengent knowledge factory-draft \
  --task <candidate_draft|incident_normalization|contradiction_cluster|dataset_draft> \
  --source-ref <path> \
  --output <path> \
  [--vendor-id <id>] \
  [--instruction <text>] \
  [--adapter stub]
```

行为：

- 默认 adapter 为 `stub`
- 可重复传 `--source-ref`
- 只生成 draft artifact
- 不修改 inbox / build / active packs

## CLI Summary Contract

CLI 输出至少包含：

- output path
- task kind
- adapter id
- review status
- source reference count

## Operator Guidance

operator 必须清楚知道：

1. 这是 factory draft，不是 active knowledge
2. 结果需要 maintainer review
3. 如果要进入正式链路，仍要手工转成 inbox/build/review/gate/activate

## Success Criteria

本阶段完成后，系统应能做到：

- 用统一接口发起 offline factory draft request
- 通过 stub adapter 生成 review-needed artifact
- artifact 保留 prompt/template provenance、source references、adapter provenance
- CLI 可直接操作
- 全程不影响 runtime facts 和 active packs
