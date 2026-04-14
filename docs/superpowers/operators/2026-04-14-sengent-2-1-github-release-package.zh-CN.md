# Sengent 2.1 GitHub Release 说明

## 版本摘要

- Sengent 1.0 的主运行时路径是 Ollama。
- Sengent 2.1 的主运行时路径改成 OpenAI-compatible API。
- support kernel 仍然是 governance-first。
- runtime truth 仍然只来自 reviewed active knowledge packs。
- hosted factory draft 仍然是 offline + review-only。

## Release 资产

建议上传到 GitHub Releases 的文件：

- `sengent-<version>.tar.gz`
- `sengent-<version>.zip`

在仓库根目录执行：

```bash
bash scripts/package_release.sh --output-dir dist
```

## 安装说明

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

### 可选的 hosted factory draft

```bash
export SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible
export SENGENT_FACTORY_HOSTED_BASE_URL=https://your-llm-endpoint.example.com
export SENGENT_FACTORY_HOSTED_MODEL=your-factory-model
export SENGENT_FACTORY_HOSTED_API_KEY=your-factory-api-key
```

### Build / Review 主机

```bash
bash scripts/install_sengent.sh --with-maintainer-tools --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

## 使用者说明

- 2.1 不是 raw-doc RAG bot
- 证据不足时，默认应该先澄清
- 如果运行时不健康，先从 `sengent doctor` 开始
- factory hosted draft 不会自动改写 runtime truth

## 维护者说明

- 不要跳过 build / review / gate / activate
- 不要让 hosted draft 直接写入 active packs
- 必须保留 rollback 和 auditability
- 要把真实客户失败 case 回填进 adversarial corpus

## Legacy 兼容说明

如果你明确还要走旧的本地模型路径，可以继续：

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
```

这是兼容模式，不是 2.1 的主发布路径。
