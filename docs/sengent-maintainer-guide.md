# Sengent Maintainer Guide

## Who This Guide Is For

这份指南给维护知识库、做版本更新、跑 gate、处理反馈闭环的同事。

你的职责有四类：

1. 新增 / 更新 / 删除资料
2. 运行 build / review / gate / activate / rollback
3. 管理 customer-site source dir
4. 把真实坏例子喂回系统

## Hard Architecture Rules

- 不要把系统改成 RAG-first
- 不要让模型主路由
- 运行时主知识源始终是 structured packs
- 原始资料只用于 build、审计和追溯
- 任何知识更新都必须先过 gate 再 activate
- 出问题优先 rollback，不要继续叠加覆盖

## Install For Maintainers

推荐安装方式：

```bash
bash scripts/install_sengent.sh --with-maintainer-tools
source .venv/bin/activate
```

如果客户内网使用自建 pip mirror，先设置：

```bash
export PIP_INDEX_URL=https://your-internal-pypi/simple
```

这会准备：

- Sengent CLI
- `pytest`
- `docling`

如果当前主机只是 build / gate 主机，不想探测 Ollama：

```bash
sengent doctor --skip-ollama
```

如果当前主机既要做运行时验证，也要做维护：

```bash
sengent doctor
```

## Default Paths

### macOS

- app home: `~/Library/Application Support/Sengent`

### Linux

- app home: `$XDG_DATA_HOME/sengent`
- fallback: `~/.local/share/sengent`

### Maintainer-relevant directories

- active source packs: `<app-home>/sources/active`
- knowledge inbox: `<app-home>/knowledge-inbox/sentieon`
- build root: `<app-home>/runtime/knowledge-build`
- activation backups: `<app-home>/runtime/knowledge-build/activation-backups`

如果你要维护一套非默认客户资料源，所有命令都显式带上 `--source-dir`：

```bash
sengent --source-dir /srv/sengent/customer-a/sources doctor --skip-ollama
sengent --source-dir /srv/sengent/customer-a/sources knowledge build
```

不要混用默认 source dir 和客户专用 source dir。

## Maintainer Workflow

### 1. Scaffold

新增或更新资料：

```bash
sengent knowledge scaffold --kind module --id fastdedup --name FastDedup
```

删除资料：

```bash
sengent knowledge scaffold --kind module --id fastdedup --action delete
```

不要直接手改 active packs。

### 2. Build

```bash
sengent knowledge build
```

如果要指定 inbox：

```bash
sengent knowledge build --inbox-dir /path/to/inbox
```

build 产物默认写到：

```text
<app-home>/runtime/knowledge-build/<build_id>/
```

关键产物：

- `report.md`
- `exceptions.jsonl`
- `candidate-packs/manifest.json`
- `parameter_promotion_review.jsonl`
- `parameter_review_suggestion.jsonl`

### 3. Review

最近一次 build：

```bash
sengent knowledge review
```

指定某次 build：

```bash
sengent knowledge review --build-id <build_id>
```

优先看：

1. `exceptions`
2. changed candidate packs
3. `parameter_review_suggestion.jsonl`

### 4. Gate

激活前必须生成这两份 gate 报告：

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

如果这两份 JSON 没写出来，`knowledge activate` 会直接阻止执行。

### 5. Activate

```bash
sengent knowledge activate --build-id <build_id>
```

activate 会：

1. 先备份当前 active packs
2. 再替换 candidate packs
3. 输出 `backup_id`
4. 写 `activation-manifest.json`

### 6. Rollback

```bash
sengent knowledge rollback --backup-id <backup_id>
```

如果你忘了 `backup_id`：

1. 先看对应 build 目录里的 `activation-manifest.json`
2. 再看 `<build-root>/activation-backups/`

不要在不知道当前回退目标的情况下继续覆盖 activation。

## Verification Levels

### A. Packaging / installer / doctor

```bash
python -m pytest -q tests/test_install_script.py tests/test_packaging_contract.py tests/test_doctor.py tests/test_app_paths.py
```

### B. Renew and runtime safety

```bash
python -m pytest -q tests/test_knowledge_build.py tests/test_cli.py tests/test_pilot_readiness.py tests/test_pilot_closed_loop.py
```

### C. Full suite

```bash
python -m pytest -q
```

### D. Release gates

```bash
python scripts/pilot_readiness_eval.py
python scripts/pilot_closed_loop.py
```

## Feedback And Closed Loop

维护原则：

- 新坏例子优先进 eval / feedback
- 不要只修代码不补 case
- 问题修复后必须重新过 closed-loop

如果 feedback JSONL 被单独导出到别的目录，但 runtime logs 在原目录：

```bash
python scripts/pilot_closed_loop.py \
  --feedback-path /path/to/runtime_feedback.jsonl \
  --runtime-root /path/to/runtime
```

## Hard Rules

- 不要手改 `sentieon-note/*.json`
- 不要跳过 gate 直接 activate
- 不要在不知道 `backup_id` 的情况下继续覆盖
- 不要把 `runtime/` 提交到 git
- 不要把 PDF parser 缺失误判成普通 runtime 故障

## Related Docs

- [README.md](../README.md)
- [docs/sengent-user-guide.md](./sengent-user-guide.md)
- [2026-04-10-sengent-knowledge-build-operator-manual.md](./superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md)
- [2026-04-10-sengent-knowledge-build-architecture.md](./superpowers/architecture/2026-04-10-sengent-knowledge-build-architecture.md)
