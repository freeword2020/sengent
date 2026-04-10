# Sengent User Guide

## 这份指南给谁看

给日常使用 Sengent 提问、排障、查模块 / 参数 / 脚本的同事看。

默认前提：

- 你已经从仓库执行过安装脚本
- 你会优先使用安装后的 `sengent` 命令
- 你不需要直接修改知识库文件

## Sengent 能做什么

Sengent 主要做四类事：

1. 帮你入门和找流程
2. 帮你排障
3. 帮你查模块 / 参数 / 脚本
4. 基于本地资料给出支持回答

它不是把文档直接丢给模型自由发挥。它的基本原则是：

- 先按规则路由
- 运行时优先使用结构化 pack
- 知识上线前要过评估门禁
- 出问题时优先回退

## 先决条件

### 支持的系统

- macOS
- Linux

### 运行时需要

- Python `3.11+`
- 本地 Ollama HTTP API
- 一个可用模型，例如 `gemma4:e4b`

### 可选能力

- `docling`
  - 只在 PDF-backed knowledge build 时需要
  - 不影响普通 query / chat

## 安装步骤

### 第 1 步: 先安装

如果这台机器要实际聊天和回答问题，建议这样装：

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
sengent doctor
```

如果这台机器只是先做 build / review，不负责聊天：

```bash
bash scripts/install_sengent.sh --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

### 第 2 步: 确认命令可用

如果你不知道下一步该输入什么命令，先看：

```bash
sengent --help
```

安装后普通用户最常用的检查是：

```bash
sengent doctor
```

### 第 3 步: 如果网络走内网镜像

先配 pip mirror，再安装：

```bash
export PIP_INDEX_URL=https://your-internal-pypi/simple
bash scripts/install_sengent.sh --skip-ollama
```

## 第一次使用前要看什么

第一次跑 `sengent doctor` 时，建议先确认这 4 件事：

- Ollama 是否能连上
- 模型是否可用
- `docling_available`
- `managed_pack_complete`

如果 `managed_pack_complete: no`，说明当前 active source packs 不完整。这通常不是你提问方式的问题，需要维护者修复安装或 source dir。

## 怎么使用

### 1. 打开对话

```bash
sengent chat
```

常用命令：

- `/help`
- `/quit`
- `/reset`
- `/feedback`

### 2. 直接提一个问题

```bash
sengent "DNAscope 是做什么的"
sengent "sentieon-cli dnascope 的 --pcr_free 是什么"
sengent "能给个 rnaseq 的参考脚本吗"
```

### 3. 看当前资料来源

```bash
sengent sources
sengent search SENTIEON_LICENSE
```

### 4. 临时切到另一套客户资料

如果你需要临时看别的客户现场资料源：

```bash
sengent --source-dir /path/to/customer-sources doctor --skip-ollama
sengent --source-dir /path/to/customer-sources "DNAscope 是做什么的"
```

## 如果回答不理想

你可以直接用 `/feedback`。提交前尽量保留这三样：

1. 原问题
2. 原回答
3. 你希望它怎么改

如果方便，再补一句它到底是：

- 知识缺失
- 知识过期
- 表达不清楚

## 常见问题排查

### 先记住这几条

- 运行时主知识源是 structured packs，不是原始 PDF
- 没装 `docling` 不影响普通使用，但会影响 PDF build
- Ollama CLI 不是运行时硬依赖，真正依赖的是本地 HTTP API
- 普通使用者一般不需要自己操作 build / activate / rollback

### 机器上文件放哪

macOS：

- `~/Library/Application Support/Sengent`

Linux：

- `$XDG_DATA_HOME/sengent`
- 或 `~/.local/share/sengent`

常见目录：

- active source packs: `<app-home>/sources/active`
- runtime logs: `<app-home>/runtime`
- knowledge builds: `<app-home>/runtime/knowledge-build`

如果要统一改位置：

```bash
export SENGENT_HOME=/path/to/sengent-home
```

### 什么时候找维护者

这些情况直接找维护者比较快：

- `managed_pack_complete: no`
- 需要新增 / 更新 / 删除知识
- 需要回退到旧版本知识库
- 需要 PDF build 能力，但当前 `docling_available: no`
