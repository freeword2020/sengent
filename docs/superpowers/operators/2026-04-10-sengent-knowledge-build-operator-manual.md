# Sengent Knowledge Build Operator Manual

## Audience

这份手册给日常维护资料的同事用。默认假设你不需要改 Python 代码，也不需要手改 `sentieon-note/*.json`。

你的日常目标只有两件事：

1. 把资料放对地方
2. 按流程 build / review / activate / rollback

## Daily Workflow

### Add Or Update Knowledge

如果你要新增或更新一份资料，先生成模板：

```bash
PYTHONPATH=src python3.11 -m sentieon_assist knowledge scaffold --kind module --id fastdedup --name FastDedup
```

常见 `--kind`：

- `module`
- `workflow`
- `external-format`
- `external-tool`
- `external-error`

命令会生成两份文件：

- markdown 原文模板
- `*.meta.yaml` sidecar metadata

然后你只需要：

1. 把资料正文贴进 markdown
2. 在 sidecar 里补最少的结构化字段

### Delete Knowledge

不要直接删 active pack 条目。

删除要走 retirement stub：

```bash
PYTHONPATH=src python3.11 -m sentieon_assist knowledge scaffold --kind module --id fastdedup --action delete
```

这会生成：

- `retire-fastdedup.md`
- `retire-fastdedup.meta.yaml`

然后再走 build 流程。

## Build

```bash
PYTHONPATH=src python3.11 -m sentieon_assist knowledge build --inbox-dir knowledge-inbox/sentieon
```

如果不传 `--source-dir`，系统会默认使用当前配置里的 active source dir。

build 完成后，产物会写到：

```text
runtime/knowledge-build/<build_id>/
```

关键文件：

- `report.md`
- `exceptions.jsonl`
- `candidate-packs/manifest.json`
- `parameter_promotion_review.jsonl`
- `parameter_review_suggestion.jsonl`

## Review

直接看最近一次 build：

```bash
PYTHONPATH=src python3.11 -m sentieon_assist knowledge review
```

或者指定某次 build：

```bash
PYTHONPATH=src python3.11 -m sentieon_assist knowledge review --build-id <build_id>
```

你重点只看三类东西：

1. `exceptions`
2. `changed candidate packs`
3. `parameter review suggestions`

## Gate

在 activation 之前，必须让 candidate packs 通过两条 gate：

```bash
python3.11 scripts/pilot_readiness_eval.py --source-dir runtime/knowledge-build/<build_id>/candidate-packs
python3.11 scripts/pilot_closed_loop.py --source-dir runtime/knowledge-build/<build_id>/candidate-packs
```

通过后，build 目录里应该有：

- `pilot-readiness-report.json`
- `pilot-closed-loop-report.json`

## Activate

```bash
PYTHONPATH=src python3.11 -m sentieon_assist knowledge activate --build-id <build_id>
```

activation 做的事：

1. 先备份当前 active packs
2. 再把 candidate packs 精确替换到 active source dir
3. 输出一个 `backup_id`

你需要把这个 `backup_id` 记下来。

activation 后会保留最近 3 个版本的 backup。

## Rollback

如果 activation 后发现问题，直接用刚才的 `backup_id`：

```bash
PYTHONPATH=src python3.11 -m sentieon_assist knowledge rollback --backup-id <backup_id>
```

rollback 会把那个版本的 active packs 精确恢复回来。

## Runtime Feedback And Closed Loop

runtime feedback 现在兼容两种记录：

- 新格式：`session_id + selected_turn_ids`
- 旧格式：`captured_turns`

如果 feedback JSONL 被单独导出到别的目录，但 session logs 还在原 runtime 下，closed-loop 需要显式给 `--runtime-root`：

```bash
python3.11 scripts/pilot_closed_loop.py \
  --feedback-path /path/to/runtime_feedback.jsonl \
  --runtime-root /path/to/runtime
```

## What To Do When Build Fails

### Case 1: `report.md` 存在，`exceptions.jsonl` 非空

这不是系统坏了，是资料里有异常。按 report 修：

- malformed front matter
- malformed sidecar
- duplicate candidate
- delete target missing
- parameter ambiguity

### Case 2: gate 没过

不要 activate。

先：

1. 看 `pilot-readiness-report.json`
2. 看 `pilot-closed-loop-report.json`
3. 找到具体失败 bucket
4. 修资料或 metadata 后重新 build

### Case 3: activation 后效果不对

不要继续覆盖。

直接 rollback 到刚才输出的 `backup_id`。

## Hard Rules

- 不要手改 `sentieon-note/*.json`
- 不要跳过 gate 直接 activate
- 不要在不知道 `backup_id` 的情况下继续覆盖 activation
- 不要把 `runtime/` 提交到 git

## Minimal Command Set

日常只记住这 5 条就够了：

```bash
PYTHONPATH=src python3.11 -m sentieon_assist knowledge scaffold --kind module --id <id> --name <name>
PYTHONPATH=src python3.11 -m sentieon_assist knowledge build --inbox-dir knowledge-inbox/sentieon
PYTHONPATH=src python3.11 -m sentieon_assist knowledge review
PYTHONPATH=src python3.11 -m sentieon_assist knowledge activate --build-id <build_id>
PYTHONPATH=src python3.11 -m sentieon_assist knowledge rollback --backup-id <backup_id>
```
