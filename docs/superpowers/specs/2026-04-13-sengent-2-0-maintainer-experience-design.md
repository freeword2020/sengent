# Sengent 2.0 Maintainer Experience Design

## Goal

把 maintainer 当前需要在 `knowledge review`、`parameter_review_suggestion.jsonl`、`gap_intake_review.jsonl`、`gap_eval_seed.jsonl`、candidate pack diffs 之间手工来回切换的流程，收敛成一个明确的 `maintainer queue` 与 `next action` 视图。

目标不是做复杂 UI，而是让 maintainer 在 CLI 里就能快速回答三个问题：

1. 现在这次 build 最重要的待处理项是什么？
2. 每类待处理项为什么重要？
3. 下一步该执行哪个命令？

## Scope

本阶段只做 CLI-first 的 maintainer convenience MVP。

包含：

- build 级 maintainer queue 聚合
- bucket 级 next-action 生成
- `knowledge queue` CLI
- `knowledge review` 保持原始 report 能力不变

不包含：

- 前端维护后台
- 自动 triage
- 自动 gate
- 自动 activate
- 新的 runtime 事实链

## Problem

当前系统虽然已经有完整的离线闭环，但 maintainer 仍然需要自己把多个 artifact 拼成一个工作面：

- `parameter_review_suggestion.jsonl`
- `gap_intake_review.jsonl`
- `gap_eval_seed.jsonl`
- compile skips
- candidate pack diffs
- gate reports

这对系统工程上是正确的，但对维护体验仍然偏“技术内部结构暴露”，而不是“下一步应该做什么”。

## Design Principles

### 1. Review Over Artifact Hunting

maintainer 应该先看到待处理队列，再按需钻到原始 artifact，而不是反过来。

### 2. Queue Buckets Must Map To Real Actions

每个 queue bucket 都必须对应一个清晰的下一步动作，例如：

- 补 triage
- 审参数候选
- 复核 source intake
- 跑 gate

### 3. Keep Evidence Paths Visible

queue 是导航层，不是替代证据层。每个 bucket 都必须能指回 build dir 下的原始 artifact。

### 4. Preserve Existing Build / Review / Gate / Activate Discipline

queue 只能帮助 maintainer 更快 review，不得绕过：

- build
- review
- gate
- activate

## Queue Model

maintainer queue 的 MVP 至少包含以下 buckets。

### 1. `pending-gap-triage`

来源：

- `gap_intake_review.jsonl` 中 `review_status=pending`

表示：

- runtime gap 已进入 inbox/build，但 maintainer 还没写 decision

下一步：

- 运行 `knowledge triage-gap`

### 2. `pending-source-review`

来源：

- compile skips 中 `factory intake pending review`

表示：

- source intake 已导入 inbox，但 maintainer 还没把原始材料整理成正式 candidate

下一步：

- 打开对应 markdown / sidecar
- 确认 pack metadata
- 将 `factory_intake_status` 从 `pending_review` 变成 `ready`
- 重新 build

### 3. `pending-parameter-review`

来源：

- `parameter_review_suggestion.jsonl`

表示：

- 自动抽取已发现真正参数 gap，但仍待 maintainer 审核

下一步：

- 根据 suggestion artifact 补结构化 metadata 或拒绝噪声候选

### 4. `pending-gate-input`

来源：

- `gap_eval_seed.jsonl` 非空
- 且对应 gate report 缺失或未显示通过

表示：

- build 已经产出 eval seeds，但 maintainer 还没把它们喂进 gate

下一步：

- 运行 `pilot_closed_loop.py --runtime-feedback-path <gap_eval_seed.jsonl>`

### 5. `candidate-pack-change`

来源：

- candidate pack diff 中 `added/updated/removed`

表示：

- 本次 build 确实改动了正式 candidate knowledge，需要 maintainer review

下一步：

- 查看 changed ids 与 report
- 进入 gate 或继续修正资料

## Queue Output Contract

CLI queue 输出至少包含：

- build id
- queue summary counts
- 每个非空 bucket 的：
  - bucket name
  - count
  - why it matters
  - next action
  - recommended command
  - artifact path
  - 1-3 个 sample items

如果所有 buckets 都为空，也不能只输出 “none”。应明确说明：

- 该 build 当前没有待处理 maintainer queue
- 下一步应检查 gate 是否已跑、是否满足 activate 条件

## CLI Contract

新增：

```bash
sengent knowledge queue [--build-id <id>] [--build-root <dir>]
```

行为：

- 默认读取最新 build
- 输出 queue summary
- 不修改任何文件

保留：

- `sengent knowledge review` 继续输出原始 report

推荐分工：

- `knowledge queue` 用于判断下一步
- `knowledge review` 用于深入证据

## First Implementation Slice

这次实现先做一个闭环 chunk：

1. queue 聚合模块
2. `knowledge queue` CLI
3. gap / source intake / parameter / gate / pack diff 五类 bucket

不在这次实现里做：

- contradiction bucket
- richer JSON export
- auto-linking source files beyond path strings

## Success Criteria

本阶段完成后，maintainer 应该能在一条命令里看到：

- 哪些 gap 还没 triage
- 哪些 source intake 还没 review
- 哪些 parameter suggestions 还待审核
- 是否有 eval seeds 还没进入 gate
- candidate pack 本次究竟改了什么

并且能立刻知道下一步命令，而不是继续手工翻多个 artifacts。
