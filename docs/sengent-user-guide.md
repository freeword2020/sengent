# Sengent 使用者说明

## 这份说明给谁看

给日常使用 Sengent 提问、排障、查模块 / 参数 / 脚本的同事看。

## 先记住 2.1 的定位

- Sengent 1.0 主要用 Ollama 做本地运行时
- Sengent 2.1 主运行时改成 OpenAI-compatible API
- 但 runtime truth 仍然来自 reviewed active knowledge packs
- factory hosted draft 仍然是 offline + review-only，不会直接变成运行时事实

## 安装前提

### 运行时主机

- Python `3.11+`
- OpenAI-compatible API endpoint
- runtime model id
- runtime API key

### 可选的 factory hosted draft

- factory provider / base URL / model / API key

### 兼容路径

如果你仍然要跑旧的本地模型路径，可以继续显式配置 Ollama，但这不是 2.1 的主使用方式。

## 安装步骤

### 1. 获取安装包

优先从 [GitHub Releases](https://github.com/freeword2020/sengent/releases) 下载 `sengent-<version>.tar.gz` 或 `.zip`。

如果暂时没有 release 包，也可以从仓库主页使用 `Download ZIP`。

### 2. 安装 CLI

```bash
tar -xzf sengent-<version>.tar.gz
cd sengent-<version>
bash scripts/install_sengent.sh
source .venv/bin/activate
```

### 3. 配置运行时 API

```bash
export SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible
export SENGENT_RUNTIME_LLM_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_RUNTIME_LLM_MODEL=your-runtime-model
export SENGENT_RUNTIME_LLM_API_KEY=your-runtime-api-key
```

如果你还要启用 hosted factory draft：

```bash
export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key
```

### 4. 做第一次检查

```bash
sengent doctor
```

建议优先看这几项：

- runtime provider 是否是 `openai_compatible`
- runtime `model_available` 是否是 `yes`
- `managed_pack_complete` 是否是 `yes`
- 如果配了 factory hosted，`review_only` 是否是 `yes`

### 5. 开始提问

```bash
sengent chat
```

或者直接单轮提问：

```bash
sengent "DNAscope 是做什么的"
sengent "GVCFtyper 是否可以按 interval 跑"
```

## 常用命令

```bash
sengent --help
sengent doctor
sengent chat
sengent sources
sengent search SENTIEON_LICENSE
```

## 使用边界

- Sengent 不是 raw-doc RAG bot
- 它不会把 factory draft 直接当成 truth
- 证据不足时，正确行为应是先澄清，而不是先乱猜
- 遇到真正的格式 / 结构一致性问题时，系统可能要求先走 tool-arbitration 路径

## 如果回答不理想

直接在 `chat` 里用 `/feedback`，并尽量保留：

1. 原问题
2. 原回答
3. 你觉得正确的支持结论或正确下一步

## 什么时候找维护者

这些情况直接找维护者更快：

- `managed_pack_complete: no`
- provider / model / API key 明显配置无误，但 `doctor` 仍然失败
- 需要补知识、改知识、删知识
- 需要把真实客户问题回填成题库或评测 case
