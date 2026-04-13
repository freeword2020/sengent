# Sengent 2.1 Chat Polish Trust Boundary Design

## Core Judgment

`runtime outbound trust boundary` 已经覆盖了主要的 answer-bearing hosted callsites，但 `chat polish` 仍然会把 `query` 和 `raw_response` 原样送进 hosted model。

这条路径虽然不决定 runtime truth，却仍然属于真实的 outbound runtime call。
如果不补上，这会让 `2.1` 的 trust-boundary enforcement 变成“主答复受控、润色路径裸奔”的半完成状态。

## Scope

本阶段只处理 `chat polish` 的 outbound trust-boundary enforcement。

覆盖范围：

- [render_chat_response()](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/cli.py)
- `build_chat_polish_prompt()`
- `build_chat_missing_info_prompt()`
- `chat_loop()` 持久化最小 trust-boundary summary

## Non-Goals

本阶段明确不做：

- 修改 runtime truth path
- 修改 answer/reference fallback 的 trust-boundary policy
- 改造 backend/provider transport seam
- 扩大成 item-level audit trail 方案
- 修改 tool arbitration / boundary pack

## Design Goal

一句话目标：

`Every hosted chat-polish call should consume sanitized query/raw-response inputs and emit a minimal trust-boundary summary.`

## Architecture

### 1. Reuse Runtime Outbound Policy Layer

不在 `cli.py` 里重复写一次脱敏逻辑。

应在 [runtime_outbound_trust.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/runtime_outbound_trust.py) 新增显式 policy helper：

- `chat-polish-outbound-v1`

输入：

- `query`
- `raw_response`

输出：

- sanitized `query`
- sanitized `raw_response`
- `TrustBoundaryResult`

### 2. Sanitize Before Prompt Construction

`render_chat_response()` 不能先构建 prompt 再打补丁式 scrub。

正确顺序是：

1. 先通过 `chat-polish-outbound-v1` 构造 sanitized payload
2. `build_chat_polish_prompt()` / `build_chat_missing_info_prompt()` 只消费 sanitized values
3. hosted backend 只接收 sanitized prompt

### 3. Keep Trace Minimal

本阶段不扩展为 item-level outbound audit trail，只做最小 summary 接回现有 turn event。

要求：

- `render_chat_response()` 可以把 `trust_boundary_summary` 通过轻量 trace callback 向外抛出
- `chat_loop()` 把这份 summary 带进 [build_turn_event()](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/session_events.py)
- `session_events` 继续只保存 sanitized summary，不保存原始值

### 4. Prefer Polish Summary For Polish Calls

当 `chat polish` 确实发生时，本阶段允许 turn event 的 `trust_boundary_summary` 记录 `chat-polish-outbound-v1`，因为这是当前 turn 最后一次真实 outbound hosted call。

更完整的多-step outbound audit trail 后续再做，不在这阶段混入。

## Testing Requirements

至少覆盖：

- `chat-polish-outbound-v1` 会 redaction 路径 / email / secret-like text
- `render_chat_response()` 的普通 polish prompt 不包含 raw sensitive values
- `render_chat_response()` 的 missing-info polish prompt 不包含 raw sensitive values
- `chat_loop()` 会把 `chat-polish-outbound-v1` summary 写进 session log

## Success Criteria

完成后，`2.1` 满足：

- `chat polish` 不再把 raw `query/raw_response` 送往 hosted model
- prompt builder 只消费 sanitized inputs
- `chat polish` outbound call 至少留下 summary-level audit signal
- runtime truth / arbitration / answer flow 不被改动
