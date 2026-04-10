# Local Ollama Environment

## 这份说明讲什么

Sengent 的运行时模型依赖的是 **Ollama HTTP API**，不是 GUI，也不是 `ollama` CLI 本身。

所以要分清三件事：

1. 真正必须有的东西
   - 本地 Ollama HTTP API
   - `OLLAMA_BASE_URL`
   - `OLLAMA_MODEL`
2. 安装脚本可以顺手帮你做的事
   - `ollama pull`
3. 不应该被当成硬要求的东西
   - GUI 操作
   - 系统里一定要有 `ollama` CLI

## 如果 Sengent 说模型或运行时不可用

先不要急着重装。按下面顺序检查，通常就能找到原因。

### 第 1 步: 确认这台机器本来要不要跑 Ollama

如果这是一台只做 build / review / gate 的主机，可以先跳过 Ollama 检查：

```bash
bash scripts/install_sengent.sh --with-maintainer-tools --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

如果这是一台要给用户聊天或查询的主机，就必须把 Ollama 和模型准备好。

### 第 2 步: 看 Ollama 服务是不是能访问

默认地址通常是：

```bash
http://127.0.0.1:11434
```

你可以直接试：

```bash
curl -sS http://127.0.0.1:11434/api/version
curl -sS http://127.0.0.1:11434/api/tags
```

如果这里不通，说明问题不在 Sengent 本身，而在 Ollama 服务没有起来、地址不对，或者网络没连到。

### 第 3 步: 看模型是不是已经装好

默认模型通常是：

```bash
gemma4:e4b
```

如果你有 `ollama` CLI，可以手动拉：

```bash
ollama pull gemma4:e4b
```

如果安装脚本会自动拉模型，也可以这样装：

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
```

### 第 4 步: 再跑一次检查

```bash
sengent doctor
```

如果这台主机本来就不该接 Ollama，就继续用：

```bash
sengent doctor --skip-ollama
```

## 最小要求

Sengent 只需要你满足这两个条件：

- 本地有可访问的 Ollama HTTP API
- 目标模型已可用，例如 `gemma4:e4b`

默认配置：

- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `OLLAMA_MODEL=gemma4:e4b`

## 常见场景

### 只做 build 的机器

这类机器只做：

- knowledge build
- review
- gate
- activate / rollback

这种场景下可以一直跳过 Ollama：

```bash
bash scripts/install_sengent.sh --with-maintainer-tools --skip-ollama
source .venv/bin/activate
sengent doctor --skip-ollama
```

### 给用户实际使用的机器

这类机器要跑：

- `sengent chat`
- 单轮 query
- 本地支持回答

建议这样准备：

```bash
bash scripts/install_sengent.sh --ensure-ollama-model
source .venv/bin/activate
sengent doctor
```

## 额外说明

- 运行时依赖的是 Ollama HTTP API
- 安装脚本可以把 `ollama` CLI 当成顺手工具
- 如果 CLI 缺失，安装不应该因此失败
- 以后切模型时，应该改配置，不要改代码
