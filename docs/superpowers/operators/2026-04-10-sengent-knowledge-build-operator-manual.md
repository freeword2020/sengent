# Sengent Knowledge Build Operator Manual

## Audience

这份手册给日常维护资料的同事用。默认假设你不改 Python 代码，也不手改 `sentieon-note/*.json`。

你的日常目标只有两件事：

1. 把资料放对地方
2. 按流程 build / review / gate / activate / rollback

## Preflight

第一次安装、换机器、迁移环境、或开始一轮 renew 前，先跑：

```bash
sengent doctor --skip-ollama
```

如果当前主机也承担运行时验证，再跑：

```bash
sengent doctor
```

重点看：

1. `docling_available`
2. `managed_pack_complete`
3. `missing_managed_pack_files`

说明：

- `PyYAML` 是 build runtime 的必需依赖
- `docling` 是 PDF 资料解析的可选能力
- 如果 `managed_pack_complete: no`，先补齐 active source dir 的正式 pack 文件，再做 build / activate / rollback

## Default Directories

### macOS

- app home: `~/Library/Application Support/Sengent`

### Linux

- app home: `$XDG_DATA_HOME/sengent`
- fallback: `~/.local/share/sengent`

### Operator paths

- inbox: `<app-home>/knowledge-inbox/sentieon`
- active packs: `<app-home>/sources/active`
- build root: `<app-home>/runtime/knowledge-build`
- activation backups: `<app-home>/runtime/knowledge-build/activation-backups`

## Add Or Update Knowledge

先生成模板：

```bash
sengent knowledge scaffold --kind module --id fastdedup --name FastDedup
```

常见 `--kind`：

- `module`
- `workflow`
- `external-format`
- `external-tool`
- `external-error`
- `incident`

命令会生成两份文件：

- markdown 原文模板
- `*.meta.yaml` sidecar metadata

然后你只做两件事：

1. 把资料正文贴进 markdown
2. 在 sidecar 里补最少的结构化字段

## Delete Knowledge

不要直接删 active pack 条目。

删除要走 retirement stub：

```bash
sengent knowledge scaffold --kind module --id fastdedup --action delete
```

## Build

```bash
sengent knowledge build
```

如果要明确指定 inbox：

```bash
sengent knowledge build --inbox-dir /path/to/inbox
```

build 完成后，产物默认写到：

```text
<app-home>/runtime/knowledge-build/<build_id>/
```

关键文件：

- `report.md`
- `exceptions.jsonl`
- `candidate-packs/manifest.json`
- `parameter_promotion_review.jsonl`
- `parameter_review_suggestion.jsonl`

## Review

最近一次 build：

```bash
sengent knowledge review
```

指定某次 build：

```bash
sengent knowledge review --build-id <build_id>
```

重点只看三类东西：

1. `exceptions`
2. changed candidate packs
3. `parameter_review_suggestion.jsonl`

## Gate

在 activation 之前，必须生成这两份 gate 报告：

- `pilot-readiness-report.json`
- `pilot-closed-loop-report.json`

从 repo root 执行：

```bash
python scripts/pilot_readiness_eval.py \
  --source-dir <build-root>/<build_id>/candidate-packs \
  --json-out <build-root>/<build_id>/pilot-readiness-report.json

python scripts/pilot_closed_loop.py \
  --source-dir <build-root>/<build_id>/candidate-packs \
  --json-out <build-root>/<build_id>/pilot-closed-loop-report.json
```

如果不写 `--json-out`，`knowledge activate` 会阻止执行。

## Activate

```bash
sengent knowledge activate --build-id <build_id>
```

activation 做的事：

1. 先备份当前 active packs
2. 再把 candidate packs 精确替换到 active source dir
3. 输出一个 `backup_id`
4. 在 build 目录写 `activation-manifest.json`

当前系统默认只保留最近 3 个 activation backups。

## Rollback

如果 activation 后发现问题：

```bash
sengent knowledge rollback --backup-id <backup_id>
```

如果忘了 `backup_id`：

1. 看 `<build-root>/<build_id>/activation-manifest.json`
2. 看 `<build-root>/activation-backups/`

rollback 会把指定 backup 精确恢复回 active source packs。

## Runtime Feedback And Closed Loop

runtime feedback 当前兼容两种记录：

- 新格式：`session_id + selected_turn_ids`
- 旧格式：`captured_turns`

如果某一轮已经带了 `gap_record`，可以把它正式导回 knowledge inbox：

```bash
sengent knowledge intake-gap \
  --session-id <session_id> \
  --turn-id <turn_id>
```

如果只想拿该 session 里最近一条 gap：

```bash
sengent knowledge intake-gap \
  --session-id <session_id> \
  --latest
```

这个命令会在 inbox 里生成两份 incident intake 文件：

- markdown 说明
- `*.meta.yaml` sidecar

它们默认进入 `incident-memory.json` 的候选编译链路，但仍然只是 inbox 输入，不会直接改 active packs。

如果 feedback JSONL 被单独导出到别的目录，但 session logs 还在原 runtime 下：

```bash
python scripts/pilot_closed_loop.py \
  --feedback-path /path/to/runtime_feedback.jsonl \
  --runtime-root /path/to/runtime
```

## What To Do When Something Fails

### Case 1: `exceptions.jsonl` 非空

这通常是资料问题，不是系统整体坏了。优先修：

- malformed front matter
- malformed sidecar
- duplicate candidate
- delete target missing
- parameter ambiguity

### Case 2: gate 没过

不要 activate。

先看：

1. `pilot-readiness-report.json`
2. `pilot-closed-loop-report.json`
3. 具体失败 bucket

然后修资料或 metadata，再重新 build。

### Case 2.5: runtime gap 已导入 inbox，但还没变成正式能力

这是正常状态。

继续按下面顺序做：

1. `sengent knowledge build`
2. `sengent knowledge review`
3. 看 `gap_intake_review.jsonl`
4. 补材料或修 sidecar
5. gate 通过后再 activate

### Case 3: activation 后效果不对

不要继续覆盖。

直接 rollback 到刚才的 `backup_id`。

## Hard Rules

- 不要手改 `sentieon-note/*.json`
- 不要跳过 gate 直接 activate
- 不要在不知道 `backup_id` 的情况下继续覆盖 activation
- 不要把 `runtime/` 提交到 git

## Minimal Command Set

```bash
sengent knowledge scaffold --kind module --id <id> --name <name>
sengent knowledge build
sengent knowledge review
sengent knowledge activate --build-id <build_id>
sengent knowledge rollback --backup-id <backup_id>
```
