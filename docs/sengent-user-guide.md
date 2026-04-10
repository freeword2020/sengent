# Sengent User Guide

## Who This Guide Is For

这份指南给日常使用 Sengent 提问、排障、查模块/参数/脚本的同事。

默认前提：

- 你已经从仓库执行过安装脚本
- 你会优先使用安装后的 `sengent` 命令
- 你不需要直接改知识库文件

## What Sengent Does

Sengent 主要做四类事：

1. 入门导航
2. 排障
3. 模块 / 参数 / 脚本查询
4. 基于本地资料的支持回答

它不是把文档直接丢给模型自由发挥。
它的基本原则是：

- rule-first
- structured packs first
- eval-gated activation
- rollback protected

## Supported Environment

### Operating systems

- macOS
- Linux

### Runtime requirements

- Python `3.11+`
- 本地 Ollama HTTP API
- 一个可用模型，例如 `gemma4:e4b`

### Optional capability

- `docling`
  - 只在 PDF-backed knowledge build 时需要
  - 不影响普通 query / chat

## Install

### Standard install

```bash
bash scripts/install_sengent.sh --skip-ollama
source .venv/bin/activate
```

如果机器已经准备好 Ollama，也可以直接：

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
```

### After install

安装后默认使用：

```bash
sengent
```

先确认环境：

```bash
sengent doctor
```

如果当前机器只是先做安装，不想探测 Ollama：

```bash
sengent doctor --skip-ollama
```

如果当前网络只能访问内网源，先配置 pip mirror：

```bash
export PIP_INDEX_URL=https://your-internal-pypi/simple
bash scripts/install_sengent.sh --skip-ollama
```

## First-Time Check

建议先看四件事：

- Ollama 是否可达
- 模型是否可用
- `docling_available`
- `managed_pack_complete`

如果 `managed_pack_complete: no`，说明当前 active source packs 不完整，需要让维护者修复安装或 source dir。

## Basic Usage

### Interactive chat

```bash
sengent chat
```

常用命令：

- `/help`
- `/quit`
- `/reset`
- `/feedback`

### Single query

```bash
sengent "DNAscope 是做什么的"
sengent "sentieon-cli dnascope 的 --pcr_free 是什么"
sengent "能给个 rnaseq 的参考脚本吗"
```

### Source inspection

```bash
sengent sources
sengent search SENTIEON_LICENSE
```

### Customer-site override

如果你要临时切到另一套客户资料源：

```bash
sengent --source-dir /path/to/customer-sources doctor --skip-ollama
sengent --source-dir /path/to/customer-sources "DNAscope 是做什么的"
```

## Feedback

如果你在 `chat` 过程中发现回答不理想：

1. 保留原问题
2. 尽量保留回答原文
3. 直接用 `/feedback`

建议补充的信息：

- 这是知识缺失、知识过期，还是回答表达问题
- 你期望它怎么答
- 如果能判断，补一个期望 mode / task

## Runtime Notes

- 运行时主知识源是 structured packs，不是原始 PDF
- 没装 `docling` 不影响普通使用，但会影响 PDF build
- Ollama CLI 不是运行时硬依赖；运行时依赖的是本地 HTTP API
- 如果你只是普通使用者，不需要自己操作 build / activate / rollback

## Where Files Live By Default

### macOS

- `~/Library/Application Support/Sengent`

### Linux

- `$XDG_DATA_HOME/sengent`
- 或 `~/.local/share/sengent`

### Common locations

- active source packs: `<app-home>/sources/active`
- runtime logs: `<app-home>/runtime`
- knowledge builds: `<app-home>/runtime/knowledge-build`

如需统一覆盖：

```bash
export SENGENT_HOME=/path/to/sengent-home
```

## When To Ask A Maintainer

这些情况建议直接找维护者：

- `managed_pack_complete: no`
- 需要新增 / 更新 / 删除知识
- 需要回退到旧版本知识库
- 需要 PDF build 能力但当前 `docling_available: no`
