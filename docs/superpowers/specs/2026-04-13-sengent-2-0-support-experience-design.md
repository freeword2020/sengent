# Sengent 2.0 Support Experience Design

## Goal

把当前 `Sentieon` CLI / chat 的回答，从“把命中的资料段落按 contract 输出出来”，升级成更像资深技术支持工程师的 `support answer card`。

这个阶段的目标不是改 runtime truth，也不是引入新的检索链，而是让用户在现有事实链不变的前提下，更快看懂三件事：

1. 当前判断是什么
2. 下一步该做什么
3. 还缺什么信息才能继续

## Scope

本阶段只做 `CLI-first support experience upgrade` 的第一个完整 chunk。

包含：

- support answer card presentation contract
- clarify affordance
- next-step visibility
- CLI / chat 现有展示层升级

不包含：

- 前端后台或复杂会话界面
- runtime truth rule 变更
- fake tool traces
- RAG-first answer path
- 自动激活或在线学习
- 大模型“扮演支持工程师”式自由润色

## Problem

当前回答虽然已经有 answer contract 和 evidence hierarchy，但用户体验仍有三个问题：

### 1. Raw Artifact Feel

很多回答仍然像“结构化资料命中结果”，例如：

- `【资料查询】`
- `【模块介绍】`
- `【常用参数】`
- `【资料版本】`
- `【参考资料】`

这对系统工程是正确的，但对最终用户来说仍偏内部实现暴露。

### 2. Clarify Is Correct But Weakly Actionable

系统已经会：

- 先澄清
- 告诉用户缺什么
- 在 clarify limit 后收边界

但用户未必一眼看出：

- 现在最该补哪一项
- 下一条应该怎么回

### 3. Next Step Is Not Always Visible

一些 reference / doc / module answers 虽然是对的，但“接下来可以怎么问”仍埋在段落中，不够像高质量支持对话。

## Design Principles

### 1. Presentation Layer, Not Truth Layer

support UX upgrade 只能改展示层和交互 affordance。

不能改变：

- resolver path
- evidence hierarchy
- boundary tagging
- clarify-first policy
- runtime logging

raw answer text 仍然是 runtime truth；presentation 只是在用户界面上重组。

### 2. Answer Card Must Preserve Contract Semantics

presentation 可以把多个原始 section 归并成更易读的 card 槽位，但不能伪造新的证据或结论。

例如：

- `【问题判断】` / `【模块介绍】` / `【资料说明】` 可以归并成 `当前判断`
- `【建议步骤】` / `【建议下一步】` 可以归并成 `下一步`
- `【需要确认的信息】` / `【需要补充的信息】` 可以归并成 `需要你补充`
- `【资料版本】` / `【参考资料】` / `【版本提示】` 可以归并成 `证据依据`

### 3. Clarify Must Tell The User How To Reply

只说“缺什么”还不够；必须让用户看到：

- 缺的是哪几项
- 下一条可以直接怎么回

### 4. Keep Evidence Visible But De-emphasized

证据和版本信息必须保留，但不应抢占回答主位。

用户应该先看到：

- 当前判断
- 下一步

然后再看到：

- 证据依据
- 使用边界

### 5. No Fake Competence

不允许：

- 虚构工具执行
- 虚构检索过程
- 把 lookup marker 包装成“我已经检查过你的环境”
- 用更像人的措辞掩盖证据不足

## Support Answer Card Model

`support answer card` 是展示层概念，不替代 runtime answer contract。

MVP 至少包含这些槽位：

### 1. `current_judgment`

用户当前最该看到的判断。

来源可能是：

- `【当前判断】`
- `【问题判断】`
- `【关联判断】`
- `【模块介绍】`
- `【资料说明】`
- `【流程指导】`
- `【能力说明】`
- `【资料边界】`

### 2. `next_steps`

明确的下一步动作。

来源优先级：

1. 原始回答里的 `【建议步骤】` / `【建议下一步】`
2. 如果原始回答没有 next-step section，则根据 response mode 派生安全的 follow-up guidance

派生 guidance 只能是：

- 如何继续追问
- 如何补上下文
- 如何把当前建议落到现场核验

不能添加新的事实判断。

### 3. `clarify_requirements`

当前还缺什么。

来源：

- `【需要确认的信息】`
- `【需要补充的信息】`
- `需要确认模块：...`

### 4. `reply_hint`

让用户能直接复制/套用的下一条回复骨架。

例如：

- `Sentieon 版本：<请填写>`
- `完整报错：<请粘贴原文>`
- `DNAscope 的 --pcr_free 是什么`

### 5. `evidence_basis`

展示但降权的证据槽位。

来源：

- `【资料版本】`
- `【版本提示】`
- `【参考资料】`
- `【资料查询】`

`【资料查询】` 这类内部 lookup marker 在 card 中不再作为主段落出现，而是归并到证据依据。

### 6. `boundary_notes`

显式说明当前回答边界。

来源：

- `【使用边界】`
- `【资料边界】` 中剩余边界句
- clarify limit 场景下的 boundary contract

## Response-Mode Behavior

### Clarify

目标：

- 让用户知道先补什么
- 给出下一条回复模板

表现：

- 以 `当前判断` 开头
- 明确列出 `需要你补充`
- 强制显示 `下一条可直接回复`

### Troubleshooting

目标：

- 先告诉用户当前判断
- 再告诉用户现场下一步
- 最后补排查线索和需要补充的信息

表现：

- `问题判断` 提升为主位
- `可能原因` 降到辅助位
- `建议步骤` 提升为主 next-step

### Reference / Workflow / Module / Parameter

目标：

- 让回答不止停在“资料命中结果”
- 给用户一个明确 follow-up direction

表现：

- `模块介绍` / `流程指导` / `常用参数` 归并成 `当前判断`
- 如果原回答没有 next-step，则自动补安全 follow-up guidance
- `资料查询` 降级到证据依据

### Boundary

目标：

- 明确告诉用户为什么不能答
- 告诉用户如何把问题收窄到系统支持边界内

表现：

- 保持 boundary judgment 作为主位
- `建议下一步` 保持显式
- `需要补充的材料` 转成 `需要你补充`

## CLI / Chat Contract

本阶段不改 chat runtime 的真实事件流。

保持：

- event stream 只展示真实阶段
- raw response 仍写入 session event
- `render_chat_response` 的稳定回答判定不引入 fake polish

新增：

- 在最终展示前，把 raw response 转成 support answer card
- chat panel 和 one-shot CLI query 都使用同一 presentation formatter

## First Implementation Slice

这次只做第一个闭环 chunk：

1. answer card parser / formatter
2. clarify reply hint
3. reference / module / troubleshooting 的 next-step visibility
4. chat / CLI 接入同一展示层

不在这次里做：

- 更广泛的 conversation memory polish
- richer multi-panel frontend layout
- proactive upload widget
- maintainerside feedback rewrite
- model-generated conversational paraphrase

## Success Criteria

本阶段完成后，用户在 CLI / chat 中应能更稳定地看到：

- 当前判断先于资料命中细节
- 下一步显式可见
- clarify 时知道下一条怎么回
- 证据依据仍可追溯，但不再抢主位

同时系统仍保持：

- answer contract
- evidence hierarchy
- clarify-first
- build / review / gate / activate discipline
- no fake tool traces
