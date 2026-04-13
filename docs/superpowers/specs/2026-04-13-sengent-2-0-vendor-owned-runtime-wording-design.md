# Sengent 2.0 Vendor-Owned Runtime Wording Design

## Goal

把 runtime caller 中仍属于 vendor-owned 的 wording / label / clarification text，从 kernel-facing 的 Sentieon 硬编码收口进正式 profile contract。

这次设计不是做整套 UI/i18n 系统，也不是去泛化 query lexicon，而是把当前最明确属于 vendor profile ownership 的 runtime 文本面切出来，并保持现有 Sentieon-first 行为不变。

## Scope

本阶段包含：

- runtime wording ownership audit
- kernel contract vs vendor ownership 边界
- VendorProfile 最小 wording contract 设计
- 第一实现 chunk 的工程切片

本阶段不包含：

- 第二 vendor implementation
- query lexicon generalization
- compile heuristics 改写
- physical pack names 改动
- runtime truth path 改动
- activate / rollback 改动
- 大面积品牌替换
- 删除现有 Sentieon wording 后留空

## Product Constraints

本设计继承以下长期约束：

- `Sengent` 是 evidence-grounded local software support kernel
- runtime 不是事实源
- facts / decisions / playbooks / incidents 仍只走 build/review/gate/activate
- 当前只做 Sentieon-first
- kernel 必须 profile-agnostic

## Problem

第一轮 decoupling 已经把 default vendor resolution 和 pack accessor contract 收口，但 runtime 文本层还残留一批硬编码的 Sentieon-facing wording。

这些文案不是 compile logic，也不是事实 pack 内容，但它们仍会影响：

- 缺失字段时向用户怎么追问
- capability explanation 怎么描述当前系统能做什么
- unsupported version / no-answer boundary 里请求什么材料
- open clarification slots 如何从响应文本反推 semantic slots

如果这些文字继续散落在 kernel-facing 模块里，会导致：

1. profile contract 仍不完整，新增 vendor 时必须改 kernel code 文案。
2. runtime contract 和 user-facing wording 耦合在一起，难以稳定测试。
3. 为了 decouple wording 而误伤 answer contract、clarify contract 的风险增加。

## Wording Ownership Audit

### A. 当前仍是 Kernel-Facing Hard-Coded Sentieon Content 的位置

#### 1. Field Labels And Requirement Aliases

- [support_coordinator.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/support_coordinator.py)
  - `FIELD_SLOT_LABELS["version"] = "Sentieon 版本"`
- [answering.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/answering.py)
  - `FIELD_LABELS`
  - `REQUIREMENT_FIELD_ALIASES`
  - `ask_for_missing()`
  - `_missing_field_labels()`

问题：

- semantic field ids 是 kernel contract
- 但面向用户展示的 label 当前由 kernel module 写死

#### 2. Capability Explanation Text

- [answering.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/answering.py)
  - `format_capability_explanation_answer()`

当前文案直接写了：

- “我可以帮你做这些 Sentieon 技术支持工作”
- 一组 Sentieon-first 的示例说明和 example queries

问题：

- capability answer 的 section structure 属于 kernel
- 但 vendor 名称、能力 bullets、示例问题属于 vendor-owned runtime wording

#### 3. Official Material Request Text For Boundaries

- [answering.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/answering.py)
  - unsupported-version gap record 中的：
    - `Sentieon {version} 对应的 manual / release notes`
- [answer_contracts.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/answer_contracts.py)
  - `format_unsupported_version_boundary()`
  - `format_no_answer_boundary()`

这里虽然部分内容已用 `profile.display_name`，但“应该补什么官方材料”的 phrasing 仍是半硬编码状态。

问题：

- “manual / release notes / app note” 这组材料类型和其用户可见 phrasing，更接近 vendor-owned wording asset，而不是 kernel rule

### B. 已经合理属于 Kernel Contract 的部分

这些文本仍应留在 kernel，不属于本轮迁移目标：

- [answer_contracts.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/answer_contracts.py)
  - section headers：
    - `【当前判断】`
    - `【需要确认的信息】`
    - `【建议下一步】`
    - `【资料边界】`
    - `【需要补充的材料】`
- answer contract 的 section 顺序和格式
- clarify limit 的规则与触发条件
- semantic field ids：
  - `version`
  - `error`
  - `input_type`
  - `data_type`
  - `step`
- gap record schema keys：
  - `missing_materials`
  - `gap_type`
  - `vendor_id`
  - `vendor_version`

这些定义的是 kernel protocol，不是 vendor content。

### C. 本轮明确不碰的文案或逻辑

#### 1. Query Lexicon And Matching Heuristics

- [support_coordinator.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/support_coordinator.py)
  - `CAPABILITY_PATTERNS`
  - `DECISION_SUPPORT_CUES`
  - `WORKFLOW_SLOT_PATTERNS`
  - `REFERENCE_FOLLOWUP_CANONICAL_RULES`

这些更接近 query behavior 和 intent routing，不属于 wording ownership 第一 chunk。

#### 2. Compile / Evidence / Resolver Logic

- `knowledge_build.py` compile heuristics
- `external_guides.py` / `module_index.py` query matching
- `normalize_model_answer()` 的术语归一化
- source filtering / evidence hierarchy

#### 3. Generic Kernel Boundary Phrasing

例如：

- “不能直接给出确定性建议”
- “先补齐下面列出的材料，再重新提问”

这些是跨 vendor 的 kernel behavior phrasing，暂不迁移。

## Ownership Boundary

### Kernel Owns

kernel 应继续拥有：

- answer contract 的 section structure
- clarify / boundary 的 control flow
- semantic field ids
- gap record schema
- trace / resolver path vocabulary

### Vendor Profile Owns

vendor profile 应承接：

- semantic field ids 对应的用户可见 label
- capability explanation 的 vendor-facing bullets 和 example prompts
- official material request 的 vendor-facing phrasing资产

### Shared Composition Pattern

推荐的组合方式是：

- kernel 决定“何时输出哪个 section / contract”
- vendor profile 提供 section 内会出现的 vendor-owned wording asset
- runtime renderer 在 kernel 模板中插入 vendor-owned wording

这能避免把整个 answer text system 直接塞进 profile。

## Minimal VendorProfile Extension

### Recommended Shape

为 `VendorProfile` 增加一个最小的 `runtime_wording` 资产对象。

建议引入：

- `VendorRuntimeWording` dataclass

包含最小字段：

1. `field_labels: dict[str, str]`
2. `capability_summary_lines: tuple[str, ...]`
3. `capability_example_queries: tuple[str, ...]`
4. `official_material_terms: tuple[str, ...]`

### Why This Is Minimal Enough

这个 contract 只承接“vendor-owned wording asset”，不承接：

- whole screen copy
- all section headers
- full prompt templates
- arbitrary free-form UI text registry

kernel 仍保留渲染模板，例如：

- `需要补充以下信息：{labels}`
- `【能力说明】`
- `【建议下一步】`
- `【资料边界】`

vendor profile 只提供被插进去的 asset：

- `Sentieon 版本`
- capability bullets
- `manual / release notes / app note`

### Optional Helper Layer

为了避免 runtime 模块重复拼装，建议再加极薄的 helper，而不是把复杂方法塞进 `VendorProfile` 本体：

- `field_label(vendor_id, field_name)`
- `field_alias_map(vendor_id)`
- `official_material_request(vendor_id, version_hint)`
- `capability_answer(vendor_id)` 或等价 renderer helper

这里的 helper 可以放在 `vendors` 层或一个专用 `vendor_runtime_wording.py` 中，但第一 chunk 不需要引入大新层级。

## First Implementation Chunk

第一实现 chunk 应切到只迁三块文本面：

### 1. Field Labels And Requirement Aliases

优先迁移：

- `FIELD_LABELS`
- `FIELD_SLOT_LABELS`
- `REQUIREMENT_FIELD_ALIASES`

原因：

- 风险最低
- 能直接收口 clarify label ownership
- 对 tests 最友好

### 2. Unsupported-Version Official Material Request Text

优先迁移：

- `answering.py` 中 gap record 的 `missing_materials`
- `answer_contracts.py` 中 official materials phrasing

原因：

- 它们已经半依赖 `profile.display_name`
- 再向前一步就能形成完整的 vendor-owned official-material wording contract

### 3. Capability Explanation Text

最后迁移：

- `format_capability_explanation_answer()`

原因：

- 它是典型 vendor-facing 文案
- 但比 field labels 更接近完整段落，风险稍高

## How To Preserve Sentieon-First Behavior

### 1. Keep The Same Output Strings For Sentieon

第一阶段的目标是“换 ownership，不换语义”。

Sentieon profile 提供的 wording asset 应保持与当前字符串一致或语义等价，避免打碎现有 tests 和 operator 预期。

### 2. Keep Answer Contract Headers In Kernel

不要把：

- `【当前判断】`
- `【建议下一步】`
- `【需要确认的信息】`

迁进 profile。否则会把 stable kernel protocol 误抽象成 UI skin。

### 3. Keep Semantic Field IDs Stable

clarify logic、state tracking、gap record 继续基于：

- `version`
- `error`
- `input_type`
- `data_type`
- `step`

只迁 label，不迁 semantic ids。

### 4. Preserve Existing Tests By Reasserting The Same Sentieon Outputs

第一 chunk 的测试应证明：

- 输出仍然包含 `Sentieon 版本`
- capability answer 仍然解释当前 Sentieon 支持范围
- unsupported version 仍请求同一类官方材料

## Approaches Considered

### Option A: Move All Runtime Text Into Vendor Profile

优点：

- decoupling 最彻底

缺点：

- 会把 kernel protocol 文案、section headers、generic boundary phrasing 一起塞进 profile
- 过度设计

结论：拒绝。

### Option B: Add A Minimal Vendor-Owned Runtime Wording Asset

优点：

- ownership 清晰
- 风险可控
- 不需要重建 whole UI text system

结论：采用。

### Option C: Keep Text In Runtime Modules, Only Interpolate `profile.display_name`

优点：

- 改动最小

缺点：

- `Sentieon 版本`、capability bullets、official material phrasing 仍是 kernel hard-code
- 没真正完成 wording ownership decoupling

结论：不足。

## Files Explicitly In Scope For The Future First Chunk

- `src/sentieon_assist/vendors/base.py`
- `src/sentieon_assist/vendors/sentieon/profile.py`
- `src/sentieon_assist/support_coordinator.py`
- `src/sentieon_assist/answering.py`
- `src/sentieon_assist/answer_contracts.py`
- `tests/test_vendor_profiles.py`
- `tests/test_support_coordinator.py`
- `tests/test_answering.py`

## Files Explicitly Out Of Scope For The Future First Chunk

- `knowledge_build.py`
- `doctor.py`
- `external_guides.py`
- `module_index.py`
- query lexicon / intent heuristics
- compile heuristics
- activate / rollback
- runtime truth path

## Success Criteria

本阶段完成后，应能证明：

1. runtime user-facing field labels 已不再由 kernel modules 写死
2. capability explanation 的 vendor-facing内容由 profile 提供
3. unsupported-version official material phrasing 已进入 vendor-owned wording contract
4. Sentieon-first 输出语义保持稳定
5. clarify contract、answer contract、trace contract 都未被打碎
