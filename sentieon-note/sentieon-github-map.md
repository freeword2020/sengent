# Sentieon GitHub Map

主入口:

- 官方 GitHub 组织: <https://github.com/Sentieon>

这个组织页在我整理时显示:

- 组织简介: Sentieon 的软件主要用于提升生信工具性能
- 公开仓库总数页面显示为 `18`
- 组织页可见的主要仓库包括 `sentieon-scripts`、`sentieon-models`、`sentieon-cli`

## 1. 核心判断

官方文档站和官方 GitHub 的角色不同:

- 文档站 / PDF: 解释产品、参数、流程、限制、排障
- GitHub: 提供安装入口、脚本、模型列表、容器和云部署样板

可按下面分工使用:

- 问“怎么用 / 参数什么意思 / 限制是什么”时，看文档站
- 问“有没有现成脚本 / 模型去哪拿 / 容器怎么起 / 云上怎么部署”时，看 GitHub

## 2. 最重要的仓库

### `sentieon-cli`

仓库:

- <https://github.com/Sentieon/sentieon-cli>

定位:

- 官方单命令 pipeline CLI
- 提供 `DNAscope`、`DNAscope LongRead`、`DNAscope Hybrid`、`Pangenome` 的单命令 pipeline 入口

整理时可见信息:

- 仓库描述: command-line interface for Sentieon pipelines
- 语言: Python
- 组织页显示最近更新: `Apr 1, 2026`
- GitHub release 页面显示最新 release: `v1.5.2`，日期 `Feb 9, 2026`

README 关键信息:

- README 写到可从 GitHub releases 下载 `tar.gz`
- 可直接 `pip install sentieon_cli-<version>.tar.gz`
- 也支持用 `poetry` 安装开发环境
- 支持的 pipeline:
  - `DNAscope`
  - `DNAscope LongRead`
  - `DNAscope Hybrid`
  - `Sentieon Pangenome`

什么时候查它:

- 需要单命令入口
- 需要标准化 CLI 入口
- 需要确认官方已经包装好的 pipeline 能力

### `sentieon-models`

仓库:

- <https://github.com/Sentieon/sentieon-models>

定位:

- 官方 model bundle 清单
- README 给人看
- `sentieon_models.yaml` 给程序读

整理时可见信息:

- 组织页显示最近更新: `Mar 10, 2026`
- README 明确说模型可按平台选择，且需要有效 license

模型覆盖:

- 短读长 DNAscope:
  - Illumina
  - MGI / Complete Genomics
  - Element
  - Ultima
  - Salus
- 长读长:
  - PacBio HiFi
  - ONT
- pangenome:
  - Illumina
  - Ultima
- vg giraffe:
  - Illumina
- somatic:
  - Ultima 的 TNscope bundle
- hybrid:
  - Illumina + PacBio
  - Illumina + ONT
  - Ultima + ONT
  - Ultima + PacBio

额外价值:

- README 还把 appnotes 和预印本论文串起来了
- bundle 使用 `ar` archive format，可以用 `ar t <bundle>` 查看内容

什么时候查它:

- 线程里有人问“某个平台该用哪个 model bundle”
- 需要确认 hybrid / pangenome / long-read 有没有官方模型
- 需要程序化拉取模型清单

### `sentieon-scripts`

仓库:

- <https://github.com/Sentieon/sentieon-scripts>

定位:

- 官方辅助脚本仓库

整理时可见信息:

- 组织页显示最近更新: `Jan 27, 2026`
- README 列出的主要内容:
  - example pipelines
  - `memest`
  - `merge_mnp`
  - `tnscope_filter`

适合场景:

- 需要 example shell pipeline
- 需要预估 variant caller 内存
- 需要把邻近变异按 haplotype 合并成 MNP
- 需要 TNscope filter 的脚本实现

### `sentieon-docker`

仓库:

- <https://github.com/Sentieon/sentieon-docker>

定位:

- 官方 Dockerfile 样例

README 关键信息:

- 需要 Docker `17.05+`
- 使用 multi-stage builds
- 例子里可通过 `--build-arg SENTIEON_VERSION=202503.02` 构建镜像

适合场景:

- 想快速封装 Sentieon 运行环境
- 想查看官方容器构建样例

### `terraform`

仓库:

- <https://github.com/Sentieon/terraform>

定位:

- 官方 Terraform 样板

目录:

- `aws_license-server`
- `azure_license-server`

README 关键信息:

- Azure 和 AWS 都给了 license server 的快速部署方案
- Azure 方案需要 `Terraform CLI` 和 `Azure CLI`
- AWS 方案需要 `Terraform CLI` 和 `AWS CLI`
- AWS 样板会处理安全组、日志、IAM、实例和 Route53 记录等

适合场景:

- 云上部署 license server
- 给团队做基础设施模板

### `segdup-caller`

仓库:

- <https://github.com/Sentieon/segdup-caller>

定位:

- 针对 segmental duplication 区域难基因的 specialized caller

README 关键信息:

- 明确标记 `Research Use Only`
- 适合处理高度同源基因 / 假基因区域
- 可结合 long-read 改善准确度
- 需要 Sentieon Genomics `202503` 或更高版本

已列出的支持基因包括:

- `SMN1/SMN2`
- `PMS2/PMS2CL`
- `CYP2D6/CYP2D7`
- `GBA1/GBAP1`
- `STRC/STRCP1`
- `NCF1/NCF1B`
- `CFH` 相关区域
- `CYP11B1/CYP11B2`
- `HBA1/HBA2`

适合场景:

- 线程里出现难基因、同源区域、copy number + phasing + star allele 这类问题

## 3. 其它仓库

### `sentieon-dnascope-ml`

仓库:

- <https://github.com/Sentieon/sentieon-dnascope-ml>

定位:

- 较早期的 DNAscope + ML 说明仓库
- 更像展示和脚本样例，而不是现在的总入口

能提供的价值:

- `dnascope.sh` 示例
- 对 DNAscope 机器学习模型目标和性能的解释
- 一些历史安装和评估示例

使用说明:

- 当补充“DNAscope ML 是什么、历史上怎么跑”时可参考
- 当前模型可查看 `sentieon-models`
- 当前单命令流程可查看 `sentieon-cli`

### `hap-eval`

仓库:

- <https://github.com/Sentieon/hap-eval>

定位:

- VCF comparison engine
- 适合结构变异 benchmark 相关场景

### 归档仓库

组织页还显示一些 archive 仓库，例如:

- `sentieon-dnaseq`
- `sentieon-google-genomics`

使用说明:

- 这类仓库主要用于历史参考
- 当前单命令流程、模型和参数说明分别可查看 `sentieon-cli`、`sentieon-models` 和文档站

## 4. 常见查找路径

如果需要定位不同类型资料，可按下面路径查:

1. 先看 `sentieon-models`，确认有没有对应平台 / 数据类型的 model
2. 再看 `sentieon-cli`，确认有没有现成 pipeline 入口
3. 需要 shell 范例时看 `sentieon-scripts`
4. 需要容器时看 `sentieon-docker`
5. 需要 license server 云部署时看 `terraform`
6. 需要特殊难基因能力时看 `segdup-caller`
7. 再回到文档站补参数定义、限制和排障说明

## 5. 常见问题对应仓库

### 问“有没有官方脚本 / 仓库”

- 有，官方 GitHub 组织是 `https://github.com/Sentieon`
- 标准 pipeline 可看 `sentieon-cli`
- 模型清单可看 `sentieon-models`
- 示例脚本可看 `sentieon-scripts`

### 问“模型去哪拿”

- 看 `sentieon-models`
- 它同时给出人类可读 README 和程序可读 `sentieon_models.yaml`

### 问“云上怎么起 license server”

- 看 `terraform`
- 官方已经给了 AWS / Azure 的模板

### 问“官方有没有容器样例”

- 有，看 `sentieon-docker`
