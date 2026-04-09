# Pilot Closed-Loop Adversarial Design

## Context

`Sengent` 现在已经有一条可运行的试点验收链路：

- `pilot_readiness.py` 会运行：
  - `pytest`
  - 单轮 adversarial drill
  - 高强度多轮 session drill
  - pilot 单轮 / 多轮语料
- `adversarial_sessions.py` 已经暴露每个 turn 的结构化 trace：
  - `task`
  - `issue_type`
  - `route_reason`
  - `parsed_intent`
  - `response_mode`

这让系统从“能跑对抗题”进入“能解释为什么失败”。但现在还缺一条真正的闭环：

- 新坏例子怎么进入系统
- 指标怎么汇总成一个可读分数
- 失败 bucket 怎么转成下一轮收紧优先级
- 当前结果相比上一轮是变好还是变差

## Problem Statement

当前试点评测仍然偏“静态 gate”，还不算“闭环试点对抗”。

### Gap 1: 缺少坏例子 intake 层

现在新增坏例子要直接改 `pilot_readiness_cases.json` 或
`pilot_readiness_sessions.json`。这适合固定回归，不适合试点期间持续收客户
对话。

系统缺少一层更贴近现场的 intake 语料：

- 按来源记录
- 保留原始对话
- 标记期望模式 / 任务 / reset 约束
- 能直接回放成 session

### Gap 2: 缺少评分与趋势层

现在输出里有：

- 通过/失败
- bucket
- 基本 failure 详情

但还没有：

- 总体质量分数
- bucket 权重
- 本轮相对 baseline 的升降
- 哪类问题正在变差

这会让试点阶段的判断继续依赖人工阅读大量日志。

### Gap 3: 缺少“从失败到收紧建议”的自动映射

当前失败虽然有 bucket，但还没有把 bucket 映射成下一轮具体动作：

- 该去改 `support_coordinator.py`
- 还是改 `reference_resolution.py`
- 还是补 pilot 语料
- 还是仅更新 baseline

结果就是每次复盘仍要人工重新解释“下一步修什么”。

## Design Goal

在不引入 RAG 重构、不切换到大模型主路由的前提下，把现有 pilot gate
扩展成一个闭环：

1. 新坏例子能以低摩擦方式进入系统
2. 评测结果能产出统一分数和趋势
3. bucket 能自动映射成收紧优先级
4. 输出适合试点阶段每日复跑和复盘

## Recommended Approach

### Option A: 继续手工维护现有 pilot 语料

优点：

- 实现最少
- 没有新 schema

缺点：

- 现场坏例子和正式 gate 混在一起
- 没有趋势比较
- 失败后仍然靠人工判断下一步

### Option B: 在现有 gate 之上增加闭环层

做法：

- 保留当前 `pilot_readiness` 作为正式 gate
- 新增 intake 语料文件
- 新增 score / trend / recommendation 层
- 新增统一闭环脚本，跑 gate + intake replay + baseline compare

优点：

- 复用现有结构
- 低风险
- 最符合当前 rule-first 架构

缺点：

- 会多一层报告结构

### Option C: 直接做状态化试点数据库

优点：

- 长期上限最高

缺点：

- 当前过重
- 会把工程焦点从 support 行为收紧拉到基础设施

## Recommendation

选 Option B。

这是最适合当前阶段的闭环设计：保留现有 gate，不重写评测基础，只在其上补
三件事：

- intake
- score / trend
- tightening recommendation

## Target Design

### 1. Pilot Intake Layer

新增两类 intake 数据：

- `pilot_feedback_cases.json`
- `pilot_feedback_sessions.json`

它们与正式 pilot 语料分开，职责是：

- 存放试点期间新收到的真实坏例子
- 支持带来源 metadata
- 支持 reset / reused anchor 约束
- 支持 expected mode / task / markers

这层默认不直接决定 gate 成败，而是先进入 replay 和评分层。

### 2. Closed-Loop Evaluation Layer

新增独立模块，例如 `pilot_closed_loop.py`，负责：

- 运行现有 `pilot_readiness` gate
- 运行 intake 单轮 / 多轮 replay
- 汇总 failure buckets
- 计算权重分数
- 产出建议
- 可选与 baseline 做 delta 对比

这层不改变现有 `pilot_readiness.py` 的职责。`pilot_readiness.py` 仍是正式
gate；closed-loop 层是“试点运营视图”。

### 3. Score Model

定义保守的质量分数：

- 初始满分 `100`
- 每个 failure bucket 按权重扣分
- `wrong_reset` 和 `wrong_anchor_reuse` 权重最高
- `wrong_script_handoff`、`misroute` 次之
- `over_clarify`、`under_clarify`、`wrong_boundary` 再次之
- `MVP fallback` 单独计入严重问题

结果至少输出：

- `quality_score`
- `risk_level`
- `bucket_counts`
- `mvp_fallback_hits`
- `wrong_reset_count`

### 4. Baseline Compare

支持传入一个旧的 JSON 报告作为 baseline，输出：

- score delta
- bucket delta
- gate status delta
- 新增失败 case 数

这层只做对比，不做状态持久化服务。

### 5. Tightening Recommendation Layer

按 bucket counts 生成下一轮收紧建议，格式固定：

- `priority`
- `bucket`
- `target_files`
- `why_now`
- `suggested_action`

映射原则：

- `wrong_reset` / `wrong_anchor_reuse`
  - 首看 `support_coordinator.py`
  - 次看 `support_state.py`
- `wrong_script_handoff`
  - 首看 `reference_resolution.py`
  - 次看 `workflow_index.py`
- `misroute`
  - 首看 `reference_intents.py`
  - 次看 `support_coordinator.py`
- `wrong_boundary`
  - 首看 `reference_boundaries.py`
- `over_clarify` / `under_clarify`
  - 首看 `workflow_index.py`
  - 次看 `reference_resolution.py`

### 6. CLI Surface

新增统一脚本：

- `python3 scripts/pilot_closed_loop.py`
- `python3 scripts/pilot_closed_loop.py --json-out /tmp/pilot-loop.json`
- `python3 scripts/pilot_closed_loop.py --baseline /tmp/previous.json`

输出分三段：

1. gate 状态
2. 分数与 bucket 汇总
3. tightening recommendations

## Non-Goals

本轮不做：

- 客户端 UI
- 持久化数据库
- 自动写回 baseline
- 自动改代码修 bucket
- 扩大量新知识源
- LLM-first 归因

## Validation

需要新增验证：

- intake 文件加载
- score 计算稳定
- baseline delta 稳定
- recommendation 顺序稳定
- `pilot_closed_loop.py` 的文本输出和 JSON 输出

同时保留现有 gate：

- `pytest`
- 单轮 adversarial drill
- 高强度 session drill
- pilot 单轮 / 多轮 gate
