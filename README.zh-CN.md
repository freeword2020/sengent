# Sengent

面向 Sentieon 软件支持的 governance-first CLI 支持系统。

English README: [README.md](README.md)

![Sengent Home](docs/assets/sengent-home.svg)

## 2.1 这一版改了什么

Sengent 1.0 的主运行时路径是 Ollama。

Sengent 2.1 保留原来的 support kernel 和 knowledge governance，但主运行时路径改成了 **OpenAI-compatible API**。

这个变化不意味着放松治理边界：

- runtime truth 仍然只来自 reviewed active knowledge packs
- raw docs 仍然不会直接变成 runtime truth
- factory hosted draft 仍然是 offline + review-only
- clarify-first、boundary pack、tool arbitration、rollback 仍然保留

## 先拿安装包

优先推荐：

1. 打开 [GitHub Releases](https://github.com/freeword2020/sengent/releases)
2. 下载 `sengent-<version>.tar.gz` 或 `sengent-<version>.zip`
3. 解压
4. 进入解压后的 `sengent-<version>/` 目录

如果暂时还没有 release 包，也可以：

1. 打开仓库主页
2. 点击绿色 `Code`
3. 选择 `Download ZIP`
4. 解压并进入目录

如果你是维护者，要从当前 checkout 生成 GitHub Release 资产：

```bash
bash scripts/package_release.sh --output-dir dist
```

它会生成 `dist/sengent-<version>.tar.gz` 和 `dist/sengent-<version>.zip`。

## 快速开始

### 运行时主机：使用 OpenAI-compatible API

```bash
tar -xzf sengent-<version>.tar.gz
cd sengent-<version>
bash scripts/install_sengent.sh
source .venv/bin/activate

export SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible
export SENGENT_RUNTIME_LLM_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_RUNTIME_LLM_MODEL=your-runtime-model
export SENGENT_RUNTIME_LLM_API_KEY=your-runtime-api-key

export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key

sengent doctor
sengent chat
```

如果你暂时只想启用 hosted runtime，还没准备 hosted factory，可以先只配四个 `SENGENT_RUNTIME_LLM_*` 变量。

### Build / Review 主机

```bash
tar -xzf sengent-<version>.tar.gz
cd sengent-<version>
bash scripts/install_sengent.sh --with-maintainer-tools --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

### Legacy Ollama 路径

如果你仍然要走旧的本地模型路径，2.1 也保留了显式兼容方式：

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
OLLAMA_BASE_URL=http://127.0.0.1:11434 OLLAMA_MODEL=gemma4:e4b sengent doctor
```

把它当成兼容路径，不要把它当成 2.1 的主安装方式。

## 需求

### 2.1 主运行时

- Python `3.11+`
- 一个 OpenAI-compatible API endpoint
- 可用的 runtime model id 和 API key

### 可选的 hosted factory draft

- 另一个 OpenAI-compatible endpoint，或者与 runtime 共用同一个 endpoint
- 可用的 factory model id 和 API key

### 可选 legacy runtime

- 本地 Ollama HTTP API
- 本地可用模型，例如 `gemma4:e4b`

### 核心依赖

- `rich`
- `PyYAML`

### 可选维护者依赖

- `pytest`
- `docling`

## 安装脚本会做什么

`scripts/install_sengent.sh` 现在会：

- 创建本地虚拟环境
- 从当前 checkout 以非 editable 方式安装 Sengent
- 把 managed JSON packs 复制到 active source pack 目录，其中包含 `incident-memory.json`
- 运行已安装的 `sengent doctor`
- 只在 legacy Ollama 场景下，通过 `--ensure-ollama-model` 处理旧的模型拉取

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

## Runtime 和 Factory API 配置

### 必配的 runtime 变量

```bash
export SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible
export SENGENT_RUNTIME_LLM_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_RUNTIME_LLM_MODEL=your-runtime-model
export SENGENT_RUNTIME_LLM_API_KEY=your-runtime-api-key
```

### 可选的 hosted factory 变量

```bash
export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key
```

### 可选的 runtime capability 覆盖

```bash
export SENGENT_RUNTIME_LLM_SUPPORTS_TOOLS=true
export SENGENT_RUNTIME_LLM_SUPPORTS_JSON_SCHEMA=true
export SENGENT_RUNTIME_LLM_SUPPORTS_REASONING_EFFORT=false
export SENGENT_RUNTIME_LLM_SUPPORTS_STREAMING=true
export SENGENT_RUNTIME_LLM_MAX_CONTEXT=128000
export SENGENT_RUNTIME_LLM_PROMPT_CACHE_BEHAVIOR=provider-default
```

### Legacy 兼容变量

```bash
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=gemma4:e4b
export OLLAMA_KEEP_ALIVE=30m
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

## 文档入口

- English README: [README.md](README.md)
- User guide, English: [docs/sengent-user-guide.en.md](docs/sengent-user-guide.en.md)
- User guide, Chinese: [docs/sengent-user-guide.md](docs/sengent-user-guide.md)
- Maintainer guide, English: [docs/sengent-maintainer-guide.en.md](docs/sengent-maintainer-guide.en.md)
- Maintainer guide, Chinese: [docs/sengent-maintainer-guide.md](docs/sengent-maintainer-guide.md)
- 2.1 GitHub release 说明，English: [docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.md](docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.md)
- 2.1 GitHub release 说明，中文: [docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.zh-CN.md](docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.zh-CN.md)
- Legacy Ollama 环境说明: [docs/local-ollama-environment.md](docs/local-ollama-environment.md)
