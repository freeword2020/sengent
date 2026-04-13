# Sengent 2.0 Factory Draft Review Integration Design

## Goal

把 `knowledge factory-draft` 产出的 `factory_model_draft` 从“孤立 JSON 文件”升级成 build-scoped 的正式 maintainer review todo。

本阶段的目标不是让模型产物进入 truth path，而是让 maintainer 在现有 `queue -> review -> gate -> activate` 流程里，把 factory draft 当成明确的离线 review 输入处理。

## Scope

本阶段包含：

- build-scoped factory draft placement
- `factory_model_draft` 的 build attachment contract
- maintainer queue bucket 集成
- CLI inspect / review surface
- operator guidance

本阶段不包含：

- runtime truth path 改动
- active packs 自动修改
- auto-activate
- remote provider 接入
- `knowledge build` 自动消费 factory draft

## Problem

当前 `knowledge factory-draft` 已经能产出带 provenance 的 `factory_model_draft` artifact，但它仍有三个问题：

1. `--output` 是任意路径，artifact 默认不归属于某个 build。
2. maintainer queue 看不到这些 draft，因此没有正式的 next action。
3. 维护者只能手开 JSON，review flow 没有 CLI-first inspect surface。

结果是：artifact 虽然 audit-friendly，但仍然是“离线孤岛”，没有进入 maintainer 的正式待办面。

## Hard Boundary

### 1. Factory Draft Stays Downstream

factory draft 只能进入 maintainer review surface，不能直接进入：

- runtime answering
- candidate packs
- active packs
- activation gate pass

### 2. Review Todo Is Not Truth

即使 draft 已挂到 build 上并进入 queue，它也只是：

- `review_required`
- `needs_review`
- `offline review input`

而不是：

- compiled candidate
- gated artifact
- activatable knowledge

### 3. Queue Integration Must Stay Build-Scoped

maintainer queue 是 build 级工作面，所以只有“明确 attach 到某次 build”的 factory draft 才能进入 queue。

独立 `--output` 文件仍然允许存在，但不视为正式 maintainer queue item。

## Design Principles

### 1. Canonical Placement Beats Artifact Hunting

如果 artifact 没有 canonical build location，queue 就无法稳定发现它。第一原则是先确定放置协议，再做聚合。

### 2. Attach, Don’t Promote

这次集成做的是“attach to build review flow”，不是“promote into knowledge flow”。

### 3. CLI Must Explain The Next Step

maintainer 不应只看到“有几个 draft”。CLI 必须回答：

- 为什么这些 draft 重要
- 下一步是什么
- 应该执行哪个命令

## Approaches Considered

### Option A: Keep Arbitrary Output And Let Queue Scan Broadly

优点：

- 对现有 CLI 改动最小

缺点：

- queue 无法稳定判断 artifact 属于哪次 build
- 很难生成可靠 next action
- 容易把实验性 JSON 误算成正式待办

结论：拒绝。

### Option B: Add Build Attachment And Canonical Draft Directory

做法：

- `knowledge factory-draft` 支持 `--build-id [--build-root]`
- attached draft 默认写入 `<build_dir>/factory-drafts/`
- queue 只聚合该目录内 `needs_review` 的 `factory_model_draft`
- 提供 build-scoped inspect CLI

优点：

- 和现有 maintainer queue 模型完全一致
- next action 能稳定指向 build-scoped 命令
- 不影响 standalone CLI completeness

结论：采用。

### Option C: Only Add An Inspect Command

优点：

- 维护者不用手开 JSON

缺点：

- draft 仍然不是正式 queue item
- 没有 bucket / next-action / build-level summary

结论：不足以满足目标。

## Recommended Design

### 1. Build Attachment Contract

为 `factory_model_draft` 增加 build attachment 概念。

attached 模式下：

- 命令输入 `--build-id`
- artifact 写入 `<build_dir>/factory-drafts/`
- artifact 自带 `build_id` 与 canonical artifact path 语义

standalone 模式下：

- 仍可继续使用 `--output`
- artifact 仍保持 review-needed
- 但 queue 不发现它

### 2. Canonical Draft Directory

每次 build 下新增：

```text
<build_dir>/factory-drafts/
```

目录里存放本次 build 关联的所有 `factory_model_draft` JSON artifact。

第一版不做嵌套子目录，也不引入 index 文件。queue 直接按文件读取并过滤合法 artifact。

### 3. Queue Bucket

新增 bucket：

- `pending-factory-draft-review`

来源：

- `<build_dir>/factory-drafts/*.json`
- `artifact_class == factory_model_draft`
- `review_status == needs_review`

表示：

- offline factory worker 已经给出候选 draft
- maintainer 需要检查 source evidence、draft items、review hints
- 然后决定是否把确认后的内容转回 inbox/build 路径

bucket 输出至少包含：

- count
- why it matters
- next action
- recommended command
- artifact directory
- sample draft ids / task kinds

### 4. Inspect Surface

新增：

```bash
sengent knowledge review-factory-draft [--build-id <id>] [--build-root <dir>] [--draft-id <id>]
```

行为：

- 默认读取指定 build 下的所有 attached factory drafts
- 不指定 `--draft-id` 时输出 build-level summary
- 指定 `--draft-id` 时输出单个 draft 的详细 review view

inspect 输出至少包含：

- draft id
- task kind
- created at
- review status
- why this needs review
- next action
- recommended command
- source references
- draft summary
- draft items
- review hints
- artifact path

### 5. Review Flow Contract

这次集成后的 maintainer 路径是：

1. `sengent knowledge factory-draft --build-id <id> ...`
2. `sengent knowledge queue --build-id <id>`
3. `sengent knowledge review-factory-draft --build-id <id> [--draft-id <id>]`
4. maintainer 手工把确认后的内容写回 inbox / metadata / source material
5. 重新 `knowledge build`

关键点：

- factory draft 只是 review acceleration
- 正式 knowledge 仍通过 inbox/build 进入 candidate packs

## Data Contract Additions

artifact 需要新增足够的 build/review context，至少包含：

- `build_id` 或等价 build attachment 信息
- canonical artifact path 所在 build 语义
- review guidance fields，至少能支撑 inspect surface 输出：
  - why
  - next_action
  - recommended_command

这些字段是 review UX contract，不是 truth contract。

## CLI Contract Changes

### `knowledge factory-draft`

新增支持：

- `--build-id <id>`
- `--build-root <dir>`

行为：

- 若提供 `--build-id` 且未显式提供 `--output`，自动写入 canonical build draft dir
- 若只提供 `--output`，仍写 standalone artifact
- CLI summary 需要明确该 artifact 是否已 attach 到某次 build

### `knowledge queue`

新增聚合：

- `pending-factory-draft-review`

推荐命令优先指向：

```bash
sengent knowledge review-factory-draft --build-id <id> --build-root <dir>
```

### `knowledge review-factory-draft`

新增 build-scoped factory draft inspect surface，禁止修改任何文件。

## Error Handling

### 1. Missing Build

若 `factory-draft --build-id` 指向不存在的 build，应报错，不得偷偷创建伪 build 目录。

### 2. Invalid Draft Artifact

queue / inspect 发现 JSON 非法、artifact class 不匹配、缺字段时，应忽略该文件或以可理解的方式报错，但不能影响其他 build artifacts 的正常 review。

### 3. Missing Draft Id

`review-factory-draft --draft-id` 找不到目标时，应返回明确错误，并保留 build-scoped usage 提示。

## Success Criteria

本阶段完成后，系统应能做到：

- factory draft artifacts 能附着到指定 build
- maintainer queue 能发现并汇总 attached drafts
- queue 能解释 why / next action / recommended command
- maintainer 可以用 CLI review-factory-draft 看摘要和细节，不必手开 JSON
- 全程不修改 runtime truth path，不自动进入 candidate / active packs

## First Chunk Boundary

第一完整 chunk 只做：

1. attached factory draft placement
2. queue bucket integration
3. CLI review-factory-draft inspect surface
4. tests
5. operator docs

后续可再做但不在本次范围：

- richer prioritization
- cross-draft clustering
- maintainer accept/reject commands
- automated inbox scaffold from reviewed drafts
