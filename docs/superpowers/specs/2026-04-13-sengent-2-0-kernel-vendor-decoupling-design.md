# Sengent 2.0 Kernel-Vendor Decoupling Design

## Goal

为 `Sengent 2.0` 做第一完整前置收敛，把 kernel-facing 模块里的 `Sentieon` 默认假设收口进正式 contract，而不是继续散落在 runtime caller、pack accessor 和 build/runtime helper 里。

这次设计的重点不是做第二个 vendor，也不是重写当前 Sentieon 支持链路，而是把“哪些地方允许默认 Sentieon-first，哪些地方必须走 vendor contract”切清楚。

## Scope

本阶段包含：

- kernel/vendor coupling audit
- default vendor resolution contract
- pack access contract audit
- runtime caller contract audit
- 第一实现 chunk 的工程边界

本阶段不包含：

- multi-vendor implementation
- 第二个 vendor onboarding
- runtime truth path 改动
- active packs 自动修改
- auto-activate
- 删除现有 Sentieon factual content 后留空
- 改品牌名式的大面积字符串替换

## Product Constraints

本设计继承以下长期约束：

- `Sengent` 是 evidence-grounded local software support kernel
- runtime 不是事实源，LLM 不能决定事实
- facts / decisions / playbooks / incidents 必须走 build/review/gate/activate
- domain standards 是一等知识层
- 当前只做 Sentieon-first，不做第二 vendor 落地
- kernel 必须 profile-agnostic；未来新增软件应主要替换 vendor profile / packs / eval corpus

## Problem

当前代码已经有 `vendor profile` 和 `logical pack` contract，但 kernel-facing 调用层仍存在大量隐式前提：

1. 默认 vendor resolution 仍散落在多个模块中的 `"sentieon"` 字面量。
2. pack access helpers 虽然用 logical kind，但仍把 `SENTIEON_VENDOR_ID` 硬编码在模块内部。
3. runtime caller contract 没有明确规定：当调用者没显式传 `vendor_id` 时，谁负责解析默认 vendor。
4. build/doctor 的部分入口是 profile-driven 的，但 ownership boundary 还不够稳定。

这会造成两个风险：

### 1. False Decoupling

表面上有 profile contract，实际 kernel-facing path 仍默认只有 Sentieon。

### 2. Wrong Refactor Target

如果直接去改所有出现 `sentieon` 的地方，很容易把 vendor-owned factual wording 和 kernel-owned control flow 混在一起，导致现有 Sentieon-first runtime 被打碎。

## Coupling Audit

### A. 已经合理收口到 Vendor Profile Ownership 的部分

这些耦合是合理的，应该保留在 profile 或 vendor content 层：

- [vendors/sentieon/profile.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/vendors/sentieon/profile.py)
  - `vendor_id`
  - `display_name`
  - `default_version`
  - `supported_versions`
  - `pack_manifest`
  - `clarification_policy`
  - `support_boundaries`
- [kernel/pack_runtime.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/kernel/pack_runtime.py)
  - logical pack resolution
  - required pack status
  - pack path resolution
- [tests/test_vendor_profiles.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/tests/test_vendor_profiles.py)
- [tests/test_pack_runtime.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/tests/test_pack_runtime.py)

这些模块表达的是“profile contract 长什么样”，不是“kernel 默认只支持 Sentieon”。

### B. 仍属于 Kernel-Facing Hard-Coded Sentieon Assumptions 的部分

这些地方的 `sentieon` 默认值目前仍在 kernel-facing path 上，应该迁回正式 contract。

#### 1. Runtime Caller Default Resolution

- [support_coordinator.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/support_coordinator.py)
  - `SupportRouteDecision.vendor_id` 默认值
  - `_build_route_decision()` 固定用 `SENTIEON_VENDOR_ID`
  - vendor version fallback 固定从 Sentieon profile 取
- [answering.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/answering.py)
  - `route_decision` 缺失时多处 fallback 到 `"sentieon"`

问题本质：

- caller contract 里没有统一的 `resolve_vendor_id()`
- “默认 vendor 是谁”仍由各模块私自决定

#### 2. Pack Access Wrapper Defaults

- [module_index.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/module_index.py)
- [external_guides.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/external_guides.py)
- [incident_memory.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/incident_memory.py)

这些模块已经通过 logical kind 访问 pack，但仍把 vendor id 固定写死为 Sentieon。

问题本质：

- 访问 contract 已经是 kernel shape
- 但 wrapper API 仍未暴露 `vendor_id`

#### 3. Build / Doctor Default Ownership

- [knowledge_build.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/knowledge_build.py)
  - `default_inbox_dir(product="sentieon")`
  - managed pack health helpers 仍内建 `SENTIEON_VENDOR_ID`
  - `_sentieon_profile()` / `_sentieon_pack_manifest()` helper 仍是 vendor-specific naming
- [doctor.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/doctor.py)
  - managed pack completeness 默认写死 Sentieon

这里的问题不是 pack manifest ownership，本身已经走 profile contract；问题是 default vendor ownership 仍散落在 helper 层。

### C. 本轮明确不视为 Kernel Decoupling 首要目标的部分

这些地方虽然出现 `sentieon`，但目前属于 vendor content、Sentieon-first heuristics、或 risk 过高的 compile/runtime behavior，不应在第一 chunk 里一起动。

#### 1. Vendor Content Wording

- [answering.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/answering.py)
  - `FIELD_LABELS` / `REQUIREMENT_FIELD_ALIASES` 的 Sentieon 文案
  - `format_capability_explanation_answer()` 的 Sentieon 描述
  - unsupported version 缺失材料提示里的 `Sentieon {version}`
- [support_coordinator.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/support_coordinator.py)
  - `FIELD_SLOT_LABELS` 的中文提示

这些应最终迁到 profile-owned wording contract，但现在改它们风险高，且不影响 kernel default ownership 的第一步收口。

#### 2. Vendor-Specific Compile Heuristics

- [knowledge_build.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/knowledge_build.py)
  - `_product_from_path()`
  - `_extract_script_candidates()` 中 `sentieon` CLI 过滤
  - `_module_hint_from_command_line()` 中 `sentieon-cli`
  - `_compile_candidate_entry()` 中 physical pack file 分支
  - shared `sentieon-cli` parameter coverage logic

这些属于 compile semantics 和 vendor content extraction，不适合作为第一 decoupling chunk。

#### 3. Vendor-Heavy Query Lexicons

- [external_guides.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/external_guides.py)
  - guide terms / error cues
- [module_index.py](/Users/zhuge/Documents/codex/harness/.worktrees/sengent-2.0/src/sentieon_assist/module_index.py)
  - module query heuristics

这些更接近 support behavior tuning，而不是 default vendor resolution contract。

## Design Principles

### 1. Centralize Default Vendor Resolution

“如果调用者没指定 vendor，用谁”必须只有一个正式入口，不能由各模块自行 fallback 到 `"sentieon"`。

### 2. Separate Defaulting From Ownership

当前产品仍然是 Sentieon-first，所以 default vendor 仍可以是 Sentieon。

但“默认是谁”不等于“kernel 只认识 Sentieon”。默认值应由 vendor registry contract 暴露，而不是硬编码在 runtime/build helper 中。

### 3. Thread Vendor Through Accessors Before Content

先把 vendor id 能穿过 pack accessor / runtime caller / doctor/build helper，再去碰 vendor wording 和 compile heuristics。

### 4. Preserve Physical Pack Behavior

第一阶段不改 physical pack file names，不改 active pack layout，不改 current source dir semantics。

## Approaches Considered

### Option A: Full Kernel-Wide Vendor Generalization Now

做法：

- 一次性把所有 `sentieon` 字面量改成 vendor-aware
- 连 wording、heuristics、compile logic 一起抽象

缺点：

- 风险过大
- 很难证明没破坏当前 Sentieon-first runtime
- 容易把 vendor content 和 kernel contract 混改

结论：拒绝。

### Option B: Contract The Defaulting Layer First

做法：

- 新增统一的 default vendor resolution helper
- 让 runtime caller 用它
- 让 pack accessor API 接受 `vendor_id`
- 让 doctor/build helper 的 vendor default 走同一 resolver

优点：

- 改动面小
- 风险可控
- 为下一阶段的 deeper decoupling 打下真实边界

结论：采用。

### Option C: Only Rename Helpers / Constants

做法：

- `_sentieon_profile()` 改名
- 少量常量重命名

缺点：

- 结构 ownership 没变
- runtime caller 仍会私自 fallback 到 `"sentieon"`

结论：不足以解决问题。

## Recommended First Implementation Chunk

第一实现 chunk 应只解决三件事：

### 1. Default Vendor Resolution Contract

在 `vendors` 层新增正式 helper，例如：

- `DEFAULT_VENDOR_ID`
- `resolve_vendor_id(value: str | None) -> str`
- `default_vendor_profile()`

要求：

- 当前默认仍解析为 `sentieon`
- unknown vendor 仍明确报错
- 所有 kernel-facing fallback 都改为调这个 helper，而不是字面量 `"sentieon"`

### 2. Pack Access Wrapper Contract

给这些 pack access wrappers 增加可选 `vendor_id`：

- `module_index.py`
- `external_guides.py`
- `incident_memory.py`

要求：

- 默认行为保持 Sentieon-first
- 显式传 `vendor_id` 时走同一 pack runtime contract
- 不改当前 file content、file names、query behavior

### 3. Runtime / Build Helper Caller Contract

把以下 caller 层改成通过统一 resolver 取默认 vendor：

- `support_coordinator.py`
- `answering.py`
- `doctor.py`
- `knowledge_build.py` 中仅限 default/vendor helper 和 managed-pack health helper

要求：

- 不改 compile semantics
- 不改 pack activation behavior
- 不改 runtime truth path

## Runtime Caller Contract

第一阶段后，kernel-facing caller 应遵守：

1. 如果已有 `route_decision.vendor_id`，直接使用它。
2. 如果调用点显式传入 `vendor_id`，使用它并做合法性校验。
3. 如果两者都没有，调用统一 `resolve_vendor_id(None)`。
4. 不允许再直接写 `"sentieon"` 作为 caller fallback。

## Pack Access Contract

第一阶段后，pack accessor 应遵守：

1. logical kind 继续由 kernel contract 决定
2. physical file mapping 继续由 vendor profile 决定
3. accessor 层必须允许 `vendor_id`
4. accessor 层不负责决定默认 vendor，只调用统一 resolver

## Build / Doctor Contract

第一阶段后，build/doctor 只做一层调整：

- vendor default resolution 收口
- managed pack access 的默认 vendor 收口

明确不做：

- scaffold kind / entry_type / pack_target 全面泛化
- compile candidate logic 的 vendor-neutral rewrite
- source directory layout 改造

## How To Avoid Breaking Sentieon-First Runtime

### 1. Keep Default Vendor As Sentieon

这次 decoupling 的目标是 contract ownership，不是 runtime 切换。

### 2. Do Not Change Physical File Names

继续保留：

- `sentieon-modules.json`
- `workflow-guides.json`
- `external-format-guides.json`
- `external-tool-guides.json`
- `external-error-associations.json`
- `incident-memory.json`

### 3. Do Not Touch Vendor Content Wording In This Chunk

避免把 boundary refactor 和 content rewrite 混在一起。

### 4. Add Tests Around Default Behavior

第一 chunk 的验证重点应是：

- 默认不传 vendor 时行为不变
- 显式 vendor 参数能走统一 resolver
- pack accessor / doctor / build helper 不再私自 fallback 字面量

## Files Explicitly Out Of Scope For This Chunk

本轮明确不碰这些性质的内容：

- `answering.py` 中 Sentieon-facing answer wording 重写
- `support_coordinator.py` 中 capability / slot wording 重写
- `knowledge_build.py` 中 script extraction / parameter extraction / compile semantics 的 vendor-neutral 重写
- `external_guides.py` / `module_index.py` 中 query lexicon 和 matching heuristics 的泛化
- runtime source content、active packs、truth path

## Success Criteria

本阶段完成后，应能证明：

1. kernel-facing 默认 vendor resolution 只有一个正式入口
2. pack accessor 不再在模块内部写死 `SENTIEON_VENDOR_ID`
3. runtime caller contract 明确规定 vendor 如何传递和 default
4. doctor/build 的 vendor default ownership 已收口
5. 当前 Sentieon-first runtime 行为保持稳定

## Non-Goals

这次不是为了让系统“已经支持第二 vendor”。

这次只是把未来多 vendor 所需的第一层结构边界，从“隐式约定”变成“正式 contract”。
