# Sengent 2.0 Source Intake Design

## Goal

为 `Knowledge Factory` 增加第一个正式入口：把维护者手头的本地资料导入成 `knowledge inbox` 可消费的标准化 artifacts，而不是继续依赖“手工新建 markdown + 手工补 sidecar + 手工粘贴内容”。

## Scope

本阶段只做最小可用的 `source intake`：

- 支持本地文本类资料导入
- 导入后直接生成 inbox-ready markdown
- 自动写入 provenance / review hints / source class metadata
- 明确保持 `intake -> inbox -> build -> review -> gate -> activate` 边界

本阶段不做：

- 自动抽取 structured pack entries
- 自动 contradiction scan
- 大模型 factory worker
- 远程抓取器

## Source Classes

source intake 必须区分以下来源：

- `vendor-official`
- `release-notes`
- `domain-standard`
- `support-incident`
- `maintainer-note`

这些是 `source class`，不是 runtime pack kind。

## Operator Contract

维护者通过一个新命令导入资料：

```bash
sengent knowledge intake-source \
  --source-class <class> \
  --source-path <path> \
  --kind <module|workflow|external-format|external-tool|external-error|incident> \
  --id <entry_id> \
  --name <display_name>
```

这个命令做三件事：

1. 复用现有 scaffold kind 生成正式 inbox entry 壳子
2. 把原始 source 内容导入 markdown body
3. 在 sidecar 中写入 provenance 和 review hints

## Output Contract

每个 intake source 至少产出：

- 一个 inbox markdown
- 一个 sidecar metadata 文件

sidecar 最少应包含：

- `origin: factory-source-intake`
- `source_class`
- `source_provenance`
- `review_hints`
- `version`
- `date`

其中：

- `source_provenance` 记录原始本地路径、检测到的文件类型、导入时间
- `review_hints` 记录推荐下一步和维护者应确认的点

## Markdown Contract

导入后的 markdown 至少包含：

- 标题
- source class
- 原始路径
- 导入时间
- 原始材料正文

目标不是“总结得多聪明”，而是让维护者先少做搬运工作，并保留完整原文证据。

## Boundary

source intake 只能写 inbox artifacts，不能：

- 写 active packs
- 绕过 knowledge build
- 自动激活
- 自动修改 runtime facts

## Initial File Support

本阶段支持文本类本地文件：

- `.md`
- `.markdown`
- `.txt`
- `.html`
- `.htm`
- `.json`
- `.sh`
- `.bash`
- `.zsh`

不支持的文件类型直接报错，由 maintainer 先手工转换。

## Testing

最小测试覆盖：

- source class 校验
- 不支持文件类型拒绝
- markdown / sidecar 产物字段正确
- CLI `knowledge intake-source` 成功路径
- provenance / review hints 被写入 sidecar
