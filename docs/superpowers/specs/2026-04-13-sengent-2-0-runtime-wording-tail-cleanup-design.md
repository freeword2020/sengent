# Sengent 2.0 Runtime Wording Tail Cleanup Design

## Goal

收掉 `vendor-owned runtime wording contract` 落地后的两处剩余尾项，不把这条小尾项扩成新一轮 decoupling：

1. `chat_events.py` 里仍硬编码的 field labels
2. `cli.py` capability path 尚未显式透传 `decision.vendor_id`

## Context

上一轮已经把 runtime wording 的主要 ownership 收口到 `VendorProfile.runtime_wording`。当前剩余问题不是新的架构层缺失，而是两个调用面还没完全接入既有 contract：

- `chat_events.py` 仍本地维护 `FIELD_LABELS`
- `run_query()` 在 capability 分支直接调用 `format_capability_explanation_answer()`，没有显式传递 `decision.vendor_id`

这两点会造成：

- runtime wording ownership 仍有一个 UI/event 尾项没有收口
- capability path 虽然默认仍是 Sentieon-first，但 caller contract 不完整

## Scope

本轮只包含：

- `chat_events.py` 的 missing-info event label ownership cleanup
- `cli.py` capability branch 的 vendor context threading
- 对应最小测试补齐

本轮不包含：

- query lexicon
- compile heuristics
- rules/source payload
- truth path / activate / rollback
- CLI 全面 wording sweep
- 新的 vendor wording dataclass 扩展

## Ownership Decision

### 1. `chat_events.py`

`event_check_missing_info()` 面向用户展示的字段标签属于 vendor-owned runtime wording，不应继续在模块内维护独立的 `FIELD_LABELS`。

这里不需要新 contract，直接复用现有：

- `VendorProfile.runtime_wording.field_labels`

为了保持最小改动：

- `ISSUE_TYPE_LABELS` 继续留在 `chat_events.py`
- 只替换 field-label lookup，不动 event text 模板
- `event_check_missing_info()` 增加可选 `vendor_id`
- 默认行为仍走 default vendor，保持 Sentieon-first

### 2. `cli.py`

`run_query()` 的 capability branch 已经通过 `select_support_route()` 得到 `decision.vendor_id`。这里 caller 应显式把它传给：

- `format_capability_explanation_answer(vendor_id=decision.vendor_id)`

这不是新的 decoupling 设计，只是把上一轮已建立的 contract 在线路上接完整。

## Implementation Shape

### `chat_events.py`

建议增加极薄 helper：

- `_field_labels(vendor_id: str | None = None) -> dict[str, str]`

实现方式：

- `vendor_id is None` 时走 `resolve_vendor_id(None)`
- 再用 `get_vendor_profile(...).runtime_wording.field_labels`

`event_check_missing_info()` 改为：

- 签名：`event_check_missing_info(missing_fields: list[str], *, vendor_id: str | None = None) -> str`
- 渲染模板保持不变

### `cli.py`

只改 capability 分支这一行：

- 现状：`format_capability_explanation_answer()`
- 目标：`format_capability_explanation_answer(vendor_id=decision.vendor_id)`

## Compatibility Requirements

必须保持：

- 默认行为仍输出 `Sentieon 版本`
- 现有 capability answer 的 Sentieon-first内容不变
- `run_query("你能做什么")` 的表现不变
- 不影响非-capability path

## Risks

风险很低，主要是两类：

1. `chat_events.py` 额外引入 vendor resolution 后，默认路径若写错会影响 UI event 文案
2. `cli.py` capability branch 若透传参数方式不兼容，会影响 capability answer 测试

这两类风险都可以通过 focused pytest 覆盖。

## First And Only Chunk

这条尾项建议只做一个完整 chunk：

1. 先补红灯测试
2. 改 `chat_events.py`
3. 改 `cli.py`
4. 跑 focused verification

不再拆更细，也不继续向其他 caller 扩散。
