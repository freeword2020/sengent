# Sengent

面向本地 Sentieon 技术支持助手的离线 CLI 工具。

English README: [README.md](README.md)

![Sengent Home](docs/assets/sengent-home.svg)

## Sengent 是什么

Sengent 是一个本地支持系统，主要用来做这些事：

- 新人上手和流程说明
- 排障
- 查询模块 / 参数 / 脚本
- 通过 build / gate / activate / rollback 做受控知识更新

它刻意不是“先检索再聊天”的 RAG 工具，也不是“让模型自己决定路由”的模型优先路由器。

## 设计意图

Sengent 按下面 5 条规则设计：

- 先按规则路由
- 运行时以结构化 pack 为准
- 原始文档只用于 build、审计和追溯
- 知识上线前必须经过评估门禁
- 每次应用前后都要有备份和回退能力

本地模型是运行时的一部分，但只负责受控生成回答。
它不负责顶层路由，也不定义运行时事实。

## 运行时架构

系统主要有两条路径：

1. 运行时支持路径
   - `support_coordinator`
   - 确定性的参考 / 流程 / 模块访问
   - 受控回答生成
   - 会话 / 事件 / 反馈记录
2. 知识更新路径
   - 原始资料 / sidecar 元数据
   - `knowledge build`
   - 候选 pack
   - gate
   - `knowledge activate`
   - 自动备份
   - `knowledge rollback`

## 兼容性

- macOS: 支持
- Linux: 支持
- Windows: 不是本交付的主要目标

## 先把安装包拿到本地

优先推荐：

1. 打开 [GitHub Releases](https://github.com/freeword2020/sengent/releases)
2. 下载 `sengent-<version>.tar.gz` 或 `sengent-<version>.zip`
3. 解压
4. 进入解压后的 `sengent-<version>/` 目录

如果暂时还没有 release 包，也可以：

1. 打开仓库主页
2. 点击绿色 `Code`
3. 选择 `Download ZIP`
4. 解压并进入解压后的目录

如果你是维护者，需要从当前 checkout 生成 GitHub Release 压缩包：

```bash
bash scripts/package_release.sh --output-dir dist
```

这会同时生成 `dist/sengent-<version>.tar.gz` 和 `dist/sengent-<version>.zip`，可直接上传到 GitHub Releases。

## 普通用户快速开始

如果你希望这台机器装完就能聊天和问答，建议这样装：

```bash
tar -xzf sengent-0.1.0.tar.gz
cd sengent-0.1.0
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
sengent doctor
sengent chat
```

如果这台机器只做知识 build / review：

```bash
tar -xzf sengent-0.1.0.tar.gz
cd sengent-0.1.0
bash scripts/install_sengent.sh --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

如果你不知道下一步该输什么命令，先看：

```bash
sengent --help
```

## 需求

### 运行时

- Python `3.11+`
- 本地 Ollama HTTP API，用于 chat / query 运行时
- 一个本地模型，例如 `gemma4:e4b`

### 核心依赖

- `rich`
- `PyYAML`

### 可选依赖

- `docling`
  - 只在 PDF 驱动的知识 build 时需要

### 维护者工具

- `pytest`
- `docling`

安装脚本会按普通用户或维护者的场景，准备合适的依赖集合。

## 安装

### 运行时主机安装

```bash
tar -xzf sengent-0.1.0.tar.gz
cd sengent-0.1.0
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
sengent doctor
sengent chat
```

这是给真正要回答问题、要运行聊天的主机准备的。

### 只做 build 的主机安装

```bash
tar -xzf sengent-0.1.0.tar.gz
cd sengent-0.1.0
bash scripts/install_sengent.sh --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

这是给只做 build / review / gate / activate 的主机准备的。

### 维护者安装

```bash
tar -xzf sengent-0.1.0.tar.gz
cd sengent-0.1.0
bash scripts/install_sengent.sh --with-maintainer-tools --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

### 安装脚本会做什么

`scripts/install_sengent.sh` 会：

- 创建本地虚拟环境
- 从当前 checkout 以非 editable 的方式安装 Sengent
- 把 6 个 managed JSON packs 复制到 active source pack 目录，其中包括 `incident-memory.json`
- 运行已安装的 `sengent doctor`
- 只有显式传入 `--ensure-ollama-model` 时，才会尝试执行 `ollama pull <model>`

常用参数：

```bash
bash scripts/install_sengent.sh --python /path/to/python3.11
bash scripts/install_sengent.sh --venv-dir /custom/.venv
bash scripts/install_sengent.sh --with-pdf-build
bash scripts/install_sengent.sh --with-maintainer-tools
bash scripts/install_sengent.sh --refresh-active-sources
bash scripts/install_sengent.sh --skip-ollama
bash scripts/install_sengent.sh --ensure-ollama-model
bash scripts/install_sengent.sh --dry-run
```

如果你的机器需要内网 Python 镜像，先设置：

```bash
export PIP_INDEX_URL=https://your-internal-pypi/simple
bash scripts/install_sengent.sh --with-maintainer-tools
```

## 安装后的命令

安装完成后，默认命令是：

```bash
sengent
```

常见用法：

```bash
sengent --help
sengent doctor
sengent chat
sengent "DNAscope 是做什么的"
sengent sources
sengent search SENTIEON_LICENSE
```

## 如果聊天运行时还没准备好

如果 Sengent 说本地模型或运行时不可用：

1. 先执行 `sengent doctor`
2. 先确认这台机器到底是不是运行时主机
3. 如果它是运行时主机，确认 Ollama HTTP API 能访问
4. 如果服务已经起来但模型没拉好，执行：

```bash
ollama pull gemma4:e4b
```

如果这台机器本来只做 build / review，请改用：

```bash
sengent doctor --skip-ollama
```

## 默认路径

默认情况下，Sengent 使用的是用户自己的 app home，而不是仓库目录。

### macOS

- app home: `~/Library/Application Support/Sengent`

### Linux

- app home: `$XDG_DATA_HOME/sengent`
- 兜底: `~/.local/share/sengent`

### 重要子目录

- active source packs: `<app-home>/sources/active`
- knowledge inbox: `<app-home>/knowledge-inbox/sentieon`
- runtime logs: `<app-home>/runtime`
- knowledge builds: `<app-home>/runtime/knowledge-build`

需要时，可以用环境变量覆盖：

- `SENGENT_HOME`
- `SENTIEON_ASSIST_SOURCE_DIR`
- `SENTIEON_ASSIST_KNOWLEDGE_DIR`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_KEEP_ALIVE`

可选的回退后端设置：

- `SENGENT_LLM_FALLBACK_BACKEND`
- `SENGENT_LLM_FALLBACK_BASE_URL`
- `SENGENT_LLM_FALLBACK_MODEL`
- `SENGENT_LLM_FALLBACK_API_KEY`

## 常用用户命令

```bash
sengent --help
sengent doctor
sengent chat
sengent "sentieon-cli dnascope 的 --pcr_free 是什么"
sengent "能给个 rnaseq 的参考脚本吗"
sengent sources
sengent search DNAscope
```

## 常用维护者命令

```bash
sengent knowledge scaffold --kind module --id fastdedup --name FastDedup
sengent knowledge build
sengent knowledge review
sengent knowledge activate --build-id <build_id>
sengent knowledge rollback --backup-id <backup_id>
```

如果是客户现场的资料包覆盖：

```bash
sengent --source-dir /path/to/customer-sources doctor --skip-ollama
sengent --source-dir /path/to/customer-sources knowledge build
```

## 测试与门禁

这两类检查都很重要：

- 运行和维护检查
  - 用 `sengent doctor`
  - 用 `sengent knowledge build/review/activate/rollback`
- 开发和发布验证
  - 跑 `python -m pytest -q`
  - 跑仓库里的 pilot gate 脚本

更完整的门禁命令，请看维护者指南。

## 文档

- English README: [README.md](README.md)
- 用户指南: [docs/sengent-user-guide.md](docs/sengent-user-guide.md)
- 维护者指南: [docs/sengent-maintainer-guide.md](docs/sengent-maintainer-guide.md)
- 本地 Ollama 说明: [docs/local-ollama-environment.md](docs/local-ollama-environment.md)
- Operator 手册: [docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md](docs/superpowers/operators/2026-04-10-sengent-knowledge-build-operator-manual.md)
- Team briefing: [docs/superpowers/operators/2026-04-10-sengent-team-briefing.md](docs/superpowers/operators/2026-04-10-sengent-team-briefing.md)
- 架构说明: [docs/superpowers/architecture/2026-04-10-sengent-knowledge-build-architecture.md](docs/superpowers/architecture/2026-04-10-sengent-knowledge-build-architecture.md)
