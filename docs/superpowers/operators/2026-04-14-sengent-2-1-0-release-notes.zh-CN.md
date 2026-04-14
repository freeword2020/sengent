# Sengent 2.1.0 Release Notes

## 版本摘要

Sengent 2.1.0 是第一版 governance-first 的 hosted-runtime 正式发布。

Sengent 1.0 的主运行时路径是 Ollama。Sengent 2.1.0 将主运行时路径改成 OpenAI-compatible API，同时保留原有治理模型：

- runtime truth 仍然只来自 reviewed active knowledge packs
- hosted factory draft 仍然仍是 offline + review-only
- clarify-first、boundary pack、tool arbitration、audit trail、rollback 仍然保留

## 新增和变化

- 主运行时路径改成 `OpenAI-compatible API`
- hosted factory drafting 已可用，但仍然只用于 review-only
- runtime 和 chat-polish 的 outbound trust-boundary 已做硬化
- hosted runtime 已有 provider-neutral request seam
- adversarial support drill 已纳入回填的真实客户 case

## 保持不变的东西

- Sengent 仍然不是 raw-doc RAG bot
- raw ingestion 仍然不会直接变成 runtime truth
- build / review / gate / activate / rollback 仍然控制知识生命周期
- deterministic diagnostics 和 tool-required boundary 仍然有效

## 安装重点

### 运行时主机

```bash
bash scripts/install_sengent.sh
source .venv/bin/activate

export SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible
export SENGENT_RUNTIME_LLM_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_RUNTIME_LLM_MODEL=your-runtime-model
export SENGENT_RUNTIME_LLM_API_KEY=your-runtime-api-key

sengent doctor
sengent chat
```

### 可选的 hosted factory drafting

```bash
export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key
```

### Legacy 兼容路径

如果你还要走旧的本地模型路径：

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
```

这是兼容路径，不是 2.1.0 的主运行时叙事。

## 验证快照

- `pytest -q`
- `python3.11 scripts/adversarial_support_drill.py`
- 通过 `bash scripts/package_release.sh --output-dir dist` 生成 release 包

## Release 资产

- `sengent-2.1.0.tar.gz`
- `sengent-2.1.0.zip`
