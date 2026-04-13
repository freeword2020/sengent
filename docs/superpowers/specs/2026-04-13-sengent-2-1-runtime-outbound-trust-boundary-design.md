# Sengent 2.1 Runtime Outbound Trust Boundary Design

## Core Judgment

`Sengent 2.1` 已经完成了 `internal hosted runtime PoC`，但当前最关键的治理缺口仍然存在：

- `Trust Boundary` 已经有 contract
- `session_events / eval_trace_plane / factory artifacts` 已经能承载 summary
- 但 runtime 真正发往 hosted LLM 的 prompt path 还没有统一经过 trust-boundary enforcement

这意味着系统已经具备 hosted runtime 能力，却还没有把“哪些内容可以出站、哪些内容必须脱敏、哪些内容只能留本地”正式接到 runtime model call 前面。

下一阶段不应该扩功能，而应该把这条治理缝隙补齐。

## Scope

本阶段只处理 `runtime outbound trust-boundary enforcement` 的第一实现 slice。

优先覆盖这些真正带有治理风险的 outbound runtime call：

- `answering.generate_model_fallback()`
- `answering.generate_reference_fallback()`
- `reference_intents.parse_reference_intent()`

本阶段可以顺手补强 `chat polish` prompt 的 trust-boundary enforcement，但不把它当成必须完成项，也不把 trace model 做大改。

## Non-Goals

本阶段明确不做：

- 修改 runtime truth path
- 让 runtime 读取 raw ingestion 作为 truth
- 修改 `build / review / gate / activate / rollback`
- 调整 boundary pack / tool arbitration 规则本身
- 改造 gateway / multi-tenant provider routing
- 做第二 vendor

## Design Goal

把 `Trust Boundary` 从：

- contract
- summary
- artifact metadata

升级成：

- runtime outbound preflight enforcement
- prompt input sanitization
- minimal traceable summary on answer-bearing runtime model calls

一句话目标：

`Every hosted runtime call should consume sanitized outbound context, not raw caller input.`

## Architecture

### 1. Keep Generic Contract Separate From Runtime Policy

现有 [trust_boundary.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/trust_boundary.py) 保持 generic：

- `OutboundContextItem`
- `TrustBoundaryDecision`
- `TrustBoundaryResult`
- redaction / filtering / summary sanitization

新增一个 runtime-specific policy layer，例如：

- `runtime_outbound_trust.py`

它负责：

- runtime prompt input 的结构化建模
- text scrubbing / redaction heuristics
- policy-specific `TrustBoundaryDecision` 构造
- 为 prompt builder 产出 sanitized inputs

generic contract 不承担 runtime policy 细节，runtime policy 也不反向污染 factory trust-boundary logic。

### 2. Runtime Policy Is Applied Before Prompt Construction

不要在 prompt string 拼好之后再做字符串级补丁式脱敏。

正确层次是：

1. caller 拿到结构化输入
2. runtime outbound policy 先构造 sanitized context
3. prompt builder 只消费 sanitized context
4. backend router 只接收 sanitized prompt

这样能保证：

- prompt builder 不会偷偷重新带回 raw values
- trust boundary summary 与实际 outbound 内容一致
- 后续 provider/gateway 层不需要再猜测 prompt 是否安全

### 3. Policy Names Stay Explicit

第一实现 slice 采用显式 policy 名称：

- `support-answer-outbound-v1`
- `reference-answer-outbound-v1`
- `reference-intent-outbound-v1`
- optional: `chat-rewrite-outbound-v1`

这样 trace / audit / eval 面能够明确知道哪类 outbound call 经过了哪条 policy。

### 4. Sanitization Should Be Conservative, Not Clever

本阶段不做复杂 DLP 平台，也不做“猜一切敏感信息”的智能分类。

第一实现 slice 只做保守、可解释的规则：

- 绝对路径 / 本地路径片段 redaction
- email redaction
- 明显 token/secret-like key-value redaction
- 空字段不出站
- session/runtime/internal metadata 不出站

来自 active knowledge 的 `source_context / evidence` 仍视为可出站内容，因为它们属于正式知识层，而不是客户现场原始材料。

## Data Model

runtime policy layer 应返回一个小而稳定的结果对象，至少包含：

- sanitized `query`
- sanitized `info`
- sanitized `source_context`
- sanitized `evidence`
- optional sanitized `raw_response`
- `TrustBoundaryResult`

这样 caller 不需要知道 redaction 细节，只负责：

- 调 policy helper
- 用 sanitized payload 构建 prompt
- 记录 summary

## Enforcement Surface

### Support Fallback

[generate_model_fallback()](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/answering.py) 必须先做 runtime trust-boundary policy，再调用 `build_support_prompt()`。

### Reference Fallback

[generate_reference_fallback()](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/answering.py) 必须先做 runtime trust-boundary policy，再调用 `build_reference_prompt()`。

### Reference Intent Parsing

[parse_reference_intent()](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/reference_intents.py) 也必须先做 runtime trust-boundary policy，因为它同样会把用户 query 发给 hosted model。

### Chat Polish

[render_chat_response()](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/cli.py) 属于 wording-polish path，而不是 truth-bearing answer generation。

因此本阶段的优先级低于上面三条。可以在不扩大 trace surface 的前提下补上 enforcement，但如果它要求重构 session event timing，则后置到下一 slice。

## Trace Strategy

本阶段只要求在 `answer-bearing runtime model calls` 上产生 minimal traceable summary。

也就是：

- `SupportAnswerTrace` 增加 optional `trust_boundary_summary`
- `cli.run_query()` / `chat_loop()` 将 answer/reference fallback 的 summary 带入 [build_turn_event()](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.1/src/sentieon_assist/session_events.py)
- `session_events` 继续只持久化 sanitized summary，不落 raw values

`reference_intent` 的 trust-boundary summary 可以先完成 enforcement，不强求第一 slice 就进 session turn event。
第一 slice 更重视 caller-side enforcement，而不是 request-level backend tracing。

## Testing Requirements

至少要新增这些测试：

- runtime outbound policy 会 redaction 路径/email/secret-like values
- support fallback prompt 不包含 raw sensitive values
- reference fallback prompt 不包含 raw sensitive values
- reference intent prompt 不包含 raw sensitive values
- session event / turn view 只持久化 summary，不持久化 redacted raw text
- hosted runtime PoC regressions 仍然通过

## Success Criteria

这一阶段完成后，`2.1` 至少满足：

- hosted runtime 的主要 answer-bearing outbound prompt 已经过 trust boundary
- prompt builder 只消费 sanitized inputs
- trust-boundary summary 与实际 outbound call 发生关联
- runtime 仍然不把 raw ingestion 当 truth
- active knowledge / arbitration / clarify-first 不退化

## Follow-On Work

这一 slice 完成后，下一优先事项才应是：

- `chat polish` outbound trace integration
- provider gateway seam 上的 trust-boundary propagation
- trace plane 对 routing-only hosted calls 的覆盖
