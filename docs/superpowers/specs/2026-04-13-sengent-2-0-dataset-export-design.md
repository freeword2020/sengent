# Sengent 2.0 Dataset Export Design

## Goal

把已经经过 maintainer 审核的 `support trace + gap review + incident context + expected answer contract`，导出成正式可追溯的 training asset。

这里的目标不是开始训练，也不是让模型接管知识库，而是把 `Knowledge Factory` 的 downstream export 边界正式落出来。

## Scope

本阶段只做 dataset export 的第一个完整 chunk。

包含：

- audited dataset export contract
- reviewed gap support sample 导出
- CLI-first / offline export 能力
- provenance / review status / vendor id / expected answer contract 保留

不包含：

- 模型训练
- 在线学习
- runtime truth path 改造
- runtime 直接消费 dataset
- playbook / incident exemplar 的全量导出
- runtime feedback 全量导出

## Problem

`Sengent 2.0` 现在已经有：

- runtime session trace
- gap intake
- maintainer gap triage
- eval seeding
- support experience contract

但还缺一层正式的 training asset 出口。

没有这层，系统虽然能：

- 记录哪里答得不好
- 给出 maintainer decision
- 生成 closed-loop eval seed

却还不能把这些“已经审核过、可用于增强 support behavior 的样本”稳定导出给后续训练链。

## Hard Boundary

### 1. Dataset Export Is Downstream Only

dataset export 只能是 `Knowledge Factory` 的 downstream output。

不能变成：

- runtime 事实来源
- active pack 替代物
- maintainer review 的捷径

正式知识仍然遵循：

`inbox -> build -> review -> gate -> activate`

训练资产只遵循：

`reviewed artifacts -> export dataset`

### 2. Training Assets Do Not Replace The Knowledge Base

训练资产的作用是增强 support behavior，例如：

- 更稳地先澄清
- 更稳地给下一步
- 更稳地守边界

不是让模型“学会事实并替代正式知识库”。

### 3. Export Must Preserve Auditability

任何 exported sample 都必须能回溯到：

- 哪个 build / review 决策
- 哪个 session / turn
- 哪个 incident artifact
- 哪个 expected answer contract

不允许只留下脱水 prompt/answer 对。

## Supported Training Asset Classes

正式分成四类，但这次只实现第一类。

### 1. `reviewed_gap_support_sample`

来源：

- `gap_intake_review.jsonl`
- `gap_eval_seed.jsonl`
- session trace
- compiled incident entry / source metadata

特点：

- 有 maintainer triage
- 有 expected mode/task
- 有可回放 support trace

这是本次实现范围。

### 2. `reviewed_runtime_feedback_sample`

来源：

- runtime feedback
- selected turns
- 后续 maintainer triage / acceptance

这次不实现。

### 3. `incident_playbook_exemplar`

来源：

- reviewed incident-memory entries
- maintainer-authored playbook notes

这次不实现。

### 4. `boundary_or_reject_exemplar`

来源：

- reviewed boundary / reject cases

这次不实现。

## First Implementation Slice

这次只导出 `reviewed_gap_support_sample`。

筛选条件：

- build 中存在 `gap_eval_seed.jsonl`
- sample 对应 gap review 已经过 maintainer triage
- review decision 为 `seed_eval`
- sample 能定位到 session trace

这是第一块最小但完整的 audited export。

## Reviewed Gap Support Sample Contract

每条样本至少包含以下字段。

### 1. Identity

- `sample_id`
- `sample_type`
- `build_id`

### 2. Vendor Context

- `vendor_id`
- `vendor_version`

### 3. Review Provenance

- `review_status`
- `review_decision`
- `review_scope`
- `review_notes`
- `expected_answer_contract`
  - `expected_mode`
  - `expected_task`

### 4. Incident Context

- `entry_id`
- `gap_type`
- `user_question`
- `known_context`
- `missing_materials`
- `captured_at`
- `incident_origin`

### 5. Support Trace

- `session_id`
- `selected_turn_ids`
- `turns`
  - `prompt`
  - `effective_query`
  - `response`
  - `response_mode`
  - `task`
  - `issue_type`
  - `support_intent`
  - `fallback_mode`
  - `reused_anchor`
  - `gap_record`

### 6. Artifact Provenance

- `source_artifacts`
  - `gap_eval_seed.jsonl`
  - `gap_intake_review.jsonl`
  - `incident-memory.json` or sidecar metadata
  - `runtime session log`

## Export Behavior

CLI-first 导出命令应是只读的。

建议入口：

```bash
sengent knowledge export-dataset --output <path> [--build-id <id>] [--build-root <dir>] [--runtime-root <dir>]
```

行为：

- 默认读取最新 build
- 只导出当前 chunk 支持的 reviewed gap samples
- 写出 JSONL
- 不修改 build、不修改 runtime、不触发 training

## Failure Handling

dataset export 不能为了凑样本而吞掉审计缺口。

如果样本缺少关键审计链，应明确标记为 skipped，例如：

- 找不到 review record
- 找不到 incident context
- 找不到 session trace

导出 summary 必须显示：

- exported count
- skipped count
- build id
- output path

## CLI Summary Contract

CLI 输出至少包含：

- build id
- sample class summary
- exported count
- skipped count
- output path

如果没有可导出的 reviewed samples，也不能假装成功导出训练资产；应明确说明当前 build 没有 audited export candidates。

## Future Extension Path

后续可以在不破坏这次 contract 的情况下扩展：

- reviewed runtime feedback sample
- reviewed incident/playbook exemplar
- boundary/reject exemplar
- richer prompt/target draft generation

但这些都必须继续遵守：

- export downstream only
- provenance 必须完整
- runtime truth path 不变

## Success Criteria

本阶段完成后，系统应能做到：

- 从 reviewed gap artifacts 导出正式 dataset JSONL
- 每条样本都能追溯到 build/review/session/turn/incident
- expected answer contract 可直接保留
- 整个 export 流程不改变 runtime 或知识编译主链
