# Local Ollama Environment

## Purpose

Sengent 的运行时模型依赖 **Ollama HTTP API**，不是 GUI，也不是 `ollama` CLI 本身。

因此要区分三件事：

1. **运行时真正依赖**
   - 本地 Ollama HTTP API
   - `OLLAMA_BASE_URL`
   - `OLLAMA_MODEL`
2. **安装脚本的可选便利**
   - `ollama pull`
3. **不应该成为硬前提的东西**
   - GUI 操作
   - `ollama` CLI 一定存在

## Minimum Runtime Requirement

Sengent 只需要你满足这两个条件：

- 本地有可访问的 Ollama HTTP API
- 目标模型已可用，例如 `gemma4:e4b`

默认配置：

- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `OLLAMA_MODEL=gemma4:e4b`

## Recommended Verification

安装后先执行：

```bash
sengent doctor
```

如果当前主机只是 build / review 主机，不准备立刻接 Ollama：

```bash
sengent doctor --skip-ollama
```

你也可以直接验证 HTTP API：

```bash
curl -sS http://127.0.0.1:11434/api/version
curl -sS http://127.0.0.1:11434/api/tags
```

## Model Preparation

如果机器上有 `ollama` CLI，并且你希望安装脚本顺手拉模型：

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
```

如果你自己准备模型：

```bash
ollama pull gemma4:e4b
```

然后再跑：

```bash
sengent doctor
```

## Portable Rules

Sengent 的工程边界如下：

- 运行时依赖的是 Ollama HTTP API
- 安装脚本可以把 `ollama` CLI 当成 best-effort 便利
- 如果 CLI 缺失，安装不应因此失败
- 未来切换模型时，应通过配置切换，而不是改代码

## Common Situations

### Build / operator host

这类机器只做：

- knowledge build
- review
- gate
- activate / rollback

这种场景下可以先完全跳过 Ollama 探测：

```bash
bash scripts/install_sengent.sh --with-maintainer-tools --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

### Runtime / support host

这类机器要跑：

- `sengent chat`
- 单轮 query
- 本地支持回答

建议：

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
sengent doctor
```

## Troubleshooting Checklist

如果 `doctor` 里 Ollama 报错，先按下面排：

1. `OLLAMA_BASE_URL` 是否正确
2. `curl <base_url>/api/version` 是否能通
3. 目标模型是否已经拉取
4. 当前 host 是否本来就应当跳过 Ollama

如果只是 build 主机，不要把 `ollama` 缺失误判成知识库 build 故障。
