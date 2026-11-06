# ScientistTwo-Codex Research Lab（Full 版）

> 面向 Codex App 的通用自主科研工作流骨架，参考公开的 ScientistTwo
> 研究流程设计。它是独立的工程实现，不是 Google 内部源代码，也不是
> Google 或 OpenAI 官方产品。

-   **目标环境**：Codex 桌面版（macOS / Windows）
-   **科研范围**：通用 AI / 机器学习研究；也可按项目适配其他计算研究领域
-   **配置规模**：6 个科研 Agent 组、27 个专业 Custom Agents
-   **控制层**：Python 3.11+ 状态机、实验记录器、证据账本和完整性审计
-   **主入口**：Codex App 项目线程中的 `$scientisttwo` Skill

------------------------------------------------------------------------

## 目录

1.  [项目概述](#1-项目概述)
2.  [架构与职责](#2-架构与职责)
3.  [环境要求](#3-环境要求)
4.  [安装部署](#4-安装部署)
5.  [配置研究问题](#5-配置研究问题)
6.  [初始化与自检](#6-初始化与自检)
7.  [在 Codex App 中启动](#7-在-codex-app-中启动)
8.  [完整科研流程](#8-完整科研流程)
9.  [候选假设与实验运行](#9-候选假设与实验运行)
10. [状态机命令参考](#10-状态机命令参考)
11. [四层完整性审计](#11-四层完整性审计)
12. [目录与产物说明](#12-目录与产物说明)
13. [并行协作与安全建议](#13-并行协作与安全建议)
14. [常见问题与恢复](#14-常见问题与恢复)
15. [能力边界](#15-能力边界)

------------------------------------------------------------------------

## 1. 项目概述

ScientistTwo-Codex Research Lab
将科研工作拆成一组可检查、可记录、可恢复的阶段：

**研究问题定义 → 文献与局限分析 → 假设生成 → Baseline 复现 → 小规模实验
→ 完整 Benchmark → 假设进化 → 最优方案选择 → 消融实验 → 论文撰写 →
同行评审 → Rebuttal → Meta Review → 完整性审计。**

项目由三层组成：

  ----------------------------------------------------------------------------------------------------
  层                      组件                    作用
  ----------------------- ----------------------- ----------------------------------------------------
  执行层                  Codex App、Custom       文献分析、提出假设、写代码、分析实验、撰写论文
                          Agents、Skills          

  控制层                  `st2` Python CLI        保存阶段状态、校验阶段流转、记录候选和实验

  证据层                  JSON /                  保留日志、指标、代码版本、引用和论文主张的追溯关系
                          JSONL、实验目录、审计   
                          Manifest                
  ----------------------------------------------------------------------------------------------------

**重要：** Python 控制层负责持久化、结构校验和阶段门禁；科研推理、Agent
分工与审稿仍由 Codex 模型执行。该项目不是一个脱离 Codex App
后就能自行启动 27 个模型 Agent 的独立调度服务。

------------------------------------------------------------------------

## 2. 架构与职责

### 2.1 六个科研 Agent 组

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Agent 组         专业 Agent                                                                                                                                     数量 职责
  ---------------- ----------------------------------------------------------------------------------------------------------------------------- --------------------- --------------------------------------------------------
  Idea Generator   `limitation_extractor`、`limitation_verifier`、`novelty_checker`、`idea_generator`、`idea_evolver`                                                5 提取研究局限、验证证据、比较相关工作、提出和进化假设

  Evaluator        `baseline_coder`、`subset_coder`、`subset_critic`、`subset_engineer`、`fullset_coder`、`fullset_critic`、`fullset_engineer`                       7 复现基线、执行小规模与完整实验、独立评价、有限工程优化

  Analyzer         `best_idea_selector`、`result_comparator`、`ablation_planner`、`ablation_coder`、`ablation_critic`                                                5 选择最优候选、比较版本、设计和验证消融实验

  Writer           `paper_drafter`、`paper_enhancer`                                                                                                                 2 根据已验证证据生成和修订论文

  Peer Review      `peer_reviewer`、`rebuttal_planner`、`rebuttal_coder`、`heldout_reviewer`                                                                         4 模拟审稿、制定答辩实验、执行补充实验、独立最终检查

  Meta Review /    `meta_reviewer`、`spec_validator`、`reference_verifier`、`method_code_auditor`                                                                    4 最终决策及实验规范、引用、方法与代码一致性审计
  Integrity                                                                                                                                                            

  **合计**                                                                                                                                                      **27** 
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### 2.2 关键决策机制

-   **Generator--Critic 分离**：提出假设的 Agent
    不应独自批准自己的假设。
-   **Subset-to-Full**：先运行低成本代表性实验；只有通过 Critic
    的候选才进入完整 Benchmark。
-   **Idea Evolution**：保留成功与失败实验记录，用证据修订后续假设。
-   **Ablation
    Attribution**：确认收益是否来自所提出的研究机制，而不是其他训练技巧或评测变化。
-   **Independent Review**：Peer Reviewer 与最终 Held-out Reviewer
    负责独立检查；模拟审稿不等于真实会议评审。
-   **Evidence
    Traceability**：论文中的定量主张必须能追溯到实验指标、运行命令和代码版本。

------------------------------------------------------------------------

## 3. 环境要求

必需：

-   当前版本 Codex App（macOS 或 Windows）。
-   Python **3.11 或更新版本**。
-   Git。
-   可运行的研究项目：代码、数据集、Baseline、评测脚本及明确的评价指标。
-   Codex App 可正常使用的模型与 Agent 功能。

按研究任务选配：

-   CUDA / GPU 驱动与深度学习框架。
-   数据集访问权限、模型权重和外部论文检索能力。
-   LaTeX 环境（例如 TeX Live / MiKTeX），用于本地编译论文。
-   需要在线 DOI / arXiv 核验时的网络访问权限。

本项目的状态管理和通用运行器只使用 Python 标准库，不要求安装
LangChain、LangGraph
或数据库服务。具体研究代码的第三方依赖应由研究项目自行声明和锁定。

------------------------------------------------------------------------

## 4. 安装部署

### 4.1 解压并打开项目

1.  下载并解压 `scientisttwo-codex-full.zip`。
2.  将 `scientisttwo-codex-full` 放在长期使用的本地目录中。
3.  启动 Codex App，选择 **Open Project / Open Folder**。
4.  打开解压后的 `scientisttwo-codex-full` 项目根目录。根目录应同时包含
    `AGENTS.md`、`.codex/`、`.agents/`、`src/` 和 `research/`。

不要只打开 `research/` 或 `.agents/` 子目录。

### 4.2 初始化 Git

在 Codex App 的集成终端中，从项目根目录执行：

``` bash
git init
git add .
git commit -m "chore: initialize ScientistTwo-Codex scaffold"
```

如果项目已经有 Git 仓库，不要重复执行
`git init`；先检查当前分支和工作区状态。

### 4.3 创建 Python 虚拟环境

**macOS / Linux**

``` bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

**Windows PowerShell**

``` powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

安装成功后，终端应能识别 `st2`
命令。若当前终端找不到命令，确认虚拟环境已经激活；也可用
`python -m scientisttwo` 运行 CLI。

### 4.4 Codex 项目权限

-   如果 Codex App 提示是否信任项目，确认目录来源可信后再选择信任。
-   初期保留默认 Sandbox 与命令审批设置。
-   仅在确实需要下载论文、安装依赖或在线核验引用时批准网络访问。
-   对训练、下载大文件、云端资源费用和删除操作逐项审查。
-   不要把 API Key、密码、访问令牌写入 Prompt、配置文件或实验日志。

------------------------------------------------------------------------

## 5. 配置研究问题

启动完整科研流程前，必须编辑：

``` text
research/problem.md
```

将所有 `[TODO]` 替换为真实信息。至少填写：

1.  **Research Question**：研究问题、重要性、目标贡献、可证伪假设。
2.  **Human SOTA**：代表性论文、作者、年份、DOI /
    arXiv、官方代码仓库和固定 Commit。
3.  **Baseline**：基线复现命令、已发表结果及其来源。
4.  **Benchmark**：数据集版本、训练/验证/测试划分、主指标、次指标、评测脚本和统计协议。
5.  **Immutable
    Constraints**：不可修改的数据、标签、划分、评测规则、许可和隐私约束。
6.  **Compute Budget**：硬件、GPU 小时、墙钟时间、Token/API
    预算和完整实验次数上限。
7.  **Human Approval**：是否要求人工批准 Baseline、完整
    Benchmark、外部费用和论文最终主张。

同时检查：

``` text
research/budget.toml
```

其中保存参考迭代预算。它是初始配置，不是适用于所有领域的固定最优值。应按实际
GPU、数据集规模、研究周期和费用调整。

**不要把"探索整个 AI 领域"作为一个没有边界的研究任务。** 没有明确
Baseline、数据划分、指标和预算时，系统应生成阻塞项报告并停止高成本实验。

------------------------------------------------------------------------

## 6. 初始化与自检

确保终端当前目录是项目根目录，并且虚拟环境已激活。

``` bash
st2 doctor
```

`doctor` 检查 Python 版本、27 个 Agent TOML、Skill、问题文件、预算文件和
TOML 配置解析情况。

初始化研究状态：

``` bash
st2 init --problem research/problem.md
```

查看状态：

``` bash
st2 status
```

查看 CLI 命令：

``` bash
st2 --help
st2 gate --help
st2 experiment --help
st2 audit --help
```

`st2 init`
会创建活动状态并写入事件账本。如果状态已经初始化，命令会拒绝覆盖。重新开始新课题时，应先备份旧项目，或建立一个新的项目副本；不要直接删除历史实验记录。

------------------------------------------------------------------------

## 7. 在 Codex App 中启动

### 7.1 检查项目指令

确认根目录存在：

-   `AGENTS.md`：PI 的全局工作规范。
-   `.codex/config.toml`：Codex Agent 并发与推理设置。
-   `.codex/agents/*.toml`：27 个专业 Agent。
-   `.agents/skills/scientisttwo/SKILL.md`：完整科研 Skill。

如果 Codex App 没有显示 Skill 或 Custom Agents：

1.  确认打开的是项目根目录。
2.  关闭并重新打开项目，必要时重启 Codex App。
3.  检查 TOML 是否存在语法错误。
4.  在项目线程中要求 Codex 检查项目配置是否被识别。

### 7.2 启动指令

在 Codex App 的项目主线程中输入：

``` text
$scientisttwo

请启动 ScientistTwo-Codex Full Research Workflow。

首先完整读取：
- AGENTS.md
- research/problem.md
- research/budget.toml
- research/state.json

执行前检查仓库、数据访问、运行环境、Baseline 和 Benchmark 规范。
如果研究问题、Baseline、数据划分、指标、评测规则或计算预算不完整，
请生成 research/blocking_inputs.md，并停止高成本实验。

请按完整流程执行：
1. Literature Research
2. Limitation Extraction & Verification
3. Novelty Evaluation
4. Seed Idea Generation
5. Baseline Reproduction
6. Subset Experiments
7. Full Benchmark Experiments
8. Idea Evolution
9. Best Idea Selection
10. Ablation Studies
11. Paper Drafting
12. Peer Review
13. Rebuttal Experiments
14. Meta Review
15. Held-out Review
16. Four-part Integrity Audit

使用专业 Custom Agents；在每个关键阶段由独立 Critic 评估。
每个阶段更新 research/state.json 和 research/ledger/events.jsonl。
每次实验保存配置、随机种子、日志、指标和代码版本。
严格遵守预算和人工审批门禁，不得伪造引用、实验结果或研究贡献。
```

### 7.3 推荐的 Codex App 协作模式

-   **主线程**：作为 PI / 控制平面，负责读取状态、分配任务和推进阶段。
-   **只读 Agent**：文献分析、引用核验、独立审稿等互相独立的任务可并行。
-   **代码 Agent**：不同候选实现使用不同 Git Worktree 或独立分支。
-   **Critic Agent**：检查实验与证据，不与被评价的代码修改任务混在一起。
-   **人工审批**：Baseline、完整
    Benchmark、外部费用和最终论文主张按项目约定审批。

Codex 子 Agent 继承主线程的权限和 Sandbox 设置。Prompt
中的"只读"属于行为约束，不是操作系统级权限隔离。不要让多个写代码的 Agent
同时修改同一个 Worktree。

------------------------------------------------------------------------

## 8. 完整科研流程

状态机的阶段顺序如下：

``` text
intake
  -> limitations
  -> seed_ideas
  -> baseline_subset
  -> subset_experiments
  -> full_set
  -> idea_evolution
  -> best_idea
  -> ablation
  -> draft
  -> peer_review
  -> rebuttal
  -> meta_review
  -> integrity_audit
  -> completed
```

失败或拒绝的阶段可能进入 `halted`。`st2`
会校验当前阶段，避免跳过门禁或在错误阶段写入决策。

  -----------------------------------------------------------------------------------------------
  阶段                    主要任务                                   通过条件 / 后续动作
  ----------------------- ------------------------------------------ ----------------------------
  Intake                  确定研究问题、数据、Baseline、预算与约束   信息完整后进入局限分析

  Limitations             提取并验证研究局限                         有证据支持的可行动局限

  Seed Ideas              生成、去重和排序候选假设                   形成可证伪的候选集合

  Baseline Subset         先复现 Baseline 的代表性子集               指标与运行过程可信

  Subset Experiments      实现候选并运行小规模实验                   Critic 返回
                                                                     `BAD`、`ENGINEER` 或 `GOOD`

  Full Set                在完整 Benchmark 上验证通过的候选          保留完整结果和运行证据

  Idea Evolution          根据失败与成功轨迹更新假设                 在预算内继续探索或转入选择

  Best Idea               选择完整验证过的最佳候选                   只能选择 `full_validated`
                                                                     候选

  Ablation                设计并运行组件消融                         证明收益归因于提出的机制

  Draft                   根据验证证据撰写论文                       每项定量主张均有证据映射

  Peer Review             模拟独立审稿                               给出分数、问题和改进建议

  Rebuttal                将重要批评转为补充实验                     重新审稿或按预算进入 Meta
                                                                     Review

  Meta Review             综合论文、审稿与答辩历史                   `ACCEPT`、`REFINE` 或
                                                                     `REJECT`

  Integrity Audit         执行四层审计                               全部检查为 `PASS` 才能完成
  -----------------------------------------------------------------------------------------------

### 8.1 关键决策解释

Subset Critic 的决策：

-   `BAD`：停止该候选并保留失败记录，转入假设进化。
-   `ENGINEER`：允许在预算内优化实现，再次运行子集实验。
-   `GOOD`：允许申请完整 Benchmark
    运行；若配置要求人工批准，应先等待批准。

Ablation Critic 的决策：

-   `GOOD`：消融证据足够，进入论文撰写。
-   `REFINE`：在预算允许时创建新候选，重新跑完整实验，并由
    `result_comparator` 判断是否更新最佳候选。
-   `REJECT`：停止当前研究路线。

Meta Reviewer 的决策：

-   `ACCEPT`：进入完整性审计。
-   `REFINE`：返回假设/实验阶段，受 Review-driven Refinement 预算限制。
-   `REJECT`：停止并保留全部研究产物。

------------------------------------------------------------------------

## 9. 候选假设与实验运行

### 9.1 登记候选假设

候选 ID 应保持唯一，例如 `H001`、`H002`。

``` bash
st2 candidate add \
  --id H001 \
  --limitation L001 \
  --hypothesis "在固定计算预算下，提出的机制能够改善跨数据集泛化" \
  --novelty 7.5
```

`--novelty` 是辅助排序分数，不是新颖性证明。

### 9.2 编写实验脚本

实验运行器不绑定 PyTorch、TensorFlow 或其他 ML
框架。你的实验脚本需要从环境变量 `ST2_METRICS_PATH`
获取指标输出路径，并写入一个 JSON 对象。

示例 Python 片段：

``` python
import json
import os
from pathlib import Path

metrics_path = Path(os.environ["ST2_METRICS_PATH"])
metrics_path.parent.mkdir(parents=True, exist_ok=True)

result = {
    "metrics": {
        "accuracy": 0.842,
        "f1": 0.811
    },
    "seed": 123,
    "dataset_split": "validation_subset",
    "config": "configs/subset.toml"
}

metrics_path.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8"
)
```

上面的数值仅用于展示格式，不能当作真实实验结果。

### 9.3 运行子集实验

``` bash
st2 experiment run \
  --phase subset \
  --candidate H001 \
  --command "python scripts/train_and_eval.py --config configs/subset.toml"
```

运行器会：

1.  创建唯一的 `research/experiments/<run-id>/` 目录。
2.  设置 `ST2_RUN_ID`、`ST2_RUN_DIR` 和 `ST2_METRICS_PATH`。
3.  执行命令并保存 `stdout.log`、`stderr.log`。
4.  读取实验脚本生成的 `metrics.json`。
5.  记录退出码、Git Commit、配置和指标。
6.  更新 `research/state.json` 与 `research/ledger/events.jsonl`。

**命令注意事项：** 运行器把命令拆成参数列表执行，不经过
Shell。因此不要在 `--command` 中使用 `&&`、管道、重定向或 Shell
变量展开。复杂流程应写成 Python/Shell 脚本文件，再将脚本作为命令运行。

实验命令必须成功退出，并生成合法 JSON
指标文件。若缺少指标或进程失败，运行器会报错，但仍保留运行目录和日志用于排查。

### 9.4 运行器冒烟测试

``` bash
st2 experiment run \
  --phase demo \
  --candidate DEMO \
  --command "python scripts/demo_experiment.py"
```

这是合成数据的运行器测试，不是科学证据。

### 9.5 数据与实验规范

-   不得使用测试集标签进行训练或超参数调优。
-   不得通过修改评测脚本、数据划分或指标定义来制造提升。
-   记录数据集版本、软件依赖、硬件、随机种子、Git Commit 和完整配置。
-   保存失败实验，不得只保留最佳结果。
-   不要将凭据、受限数据或未获授权的模型权重写入日志或 Git。

------------------------------------------------------------------------

## 10. 状态机命令参考

### 10.1 通用命令

``` bash
st2 doctor
st2 init --problem research/problem.md
st2 status
st2 --help
```

### 10.2 阶段门禁命令格式

``` bash
st2 gate <stage> \
  --decision <decision> \
  --feedback "决策依据与证据摘要"
```

候选阶段需要 `--candidate`；Peer Review 阶段必须提供 `--score`。

### 10.3 典型阶段命令示例

以下是命令格式示例。只有在 Codex Agent
已完成相应工作、你检查过证据后，才应写入门禁。

``` bash
# 1. Intake
st2 gate intake --decision accept \
  --feedback "研究问题、Benchmark 和资源预算已确认。"

# 2. Limitations
st2 gate limitations --decision accept \
  --feedback "局限均有论文或代码证据支持。"

# 3. 登记候选
st2 candidate add --id H001 \
  --limitation L001 \
  --hypothesis "可证伪的研究假设" \
  --novelty 7.5

# 4. Seed Ideas
st2 gate seed_ideas --decision accept \
  --feedback "候选已去重并完成优先级排序。"

# 5. Baseline
st2 gate baseline_subset --decision accept \
  --feedback "Baseline 已在声明的子集上复现。"

# 6. Subset
st2 gate subset_experiments --candidate H001 \
  --decision good \
  --feedback "子集实验通过独立 Critic 检查。"

# 7. Full Benchmark
st2 gate full_set --candidate H001 \
  --decision accept \
  --feedback "完整 Benchmark 已运行并保留证据。"

# 8. Idea Evolution
st2 gate idea_evolution --decision accept \
  --feedback "已完成一轮进化并登记下一轮候选。"

# 9. Best Idea
st2 gate best_idea --candidate H001 \
  --decision accept \
  --feedback "选择该完整验证候选。"

# 10. Ablation
st2 gate ablation --decision good \
  --feedback "消融实验支持所提出机制的贡献。"

# 11. Draft
st2 gate draft --decision accept \
  --feedback "论文主张均已映射到实验与引用证据。"

# 12. Peer Review（必须带分数）
st2 gate peer_review --decision accept --score 8.2 \
  --feedback "主要问题已解决，审稿诊断分达到阈值。"

# 13. Meta Review
st2 gate meta_review --decision accept \
  --feedback "综合审稿和补充实验后建议进入审计。"

# 14. Integrity Audit
st2 gate integrity_audit --decision accept \
  --feedback "最新审计报告 overall 为 PASS。"

# 查看最终状态
st2 status
```

### 10.4 重要门禁规则

-   `intake`、`limitations`、`seed_ideas`、`baseline_subset`、`full_set`、`idea_evolution`、`best_idea`、`draft`、`peer_review`、`rebuttal`、`meta_review`、`integrity_audit`
    接受 `accept / refine / reject`（部分阶段还受分数和预算约束）。
-   `subset_experiments` 接受 `bad / good / engineer`。
-   `ablation` 接受 `good / refine / reject`。
-   `subset_experiments`、`full_set`、`best_idea` 必须提供已登记的
    `--candidate`。
-   `peer_review` 必须提供 `--score`；达到 `research/budget.toml`
    中的阈值才会按接受路径推进。
-   Ablation Refinement 后重新进入 `full_set` 时，接受决策必须附带
    `--comparison update_best` 或 `--comparison keep_old`。
-   `integrity_audit` 只有在最新 `research/audit/audit-report.json` 的
    `overall` 为 `PASS` 时才能接受。

**不要机械复制上面的示例命令。** 实际阶段和决策必须以 `st2 status`
的当前状态、实验结果和 Agent 的独立评审为准。

------------------------------------------------------------------------

## 11. 四层完整性审计

审计入口：

``` text
research/audit/manifest.example.json
```

先复制模板：

**macOS / Linux**

``` bash
cp research/audit/manifest.example.json research/audit/manifest.json
```

**Windows PowerShell**

``` powershell
Copy-Item research/audit/manifest.example.json research/audit/manifest.json
```

编辑 `research/audit/manifest.json`，替换所有示例值。

### 11.1 Score Verification

-   每个主结果声明指标名称、论文报告值、容差和重放命令。
-   重放命令必须输出 JSON 对象，例如 `{"metrics":{"accuracy":0.91}}`。
-   审计器会比较重跑指标与论文报告值是否在容差内。

### 11.2 Specification Compliance

-   在 Manifest 中配置 Benchmark 规则检查命令。
-   检查脚本只有在规范满足时才应返回退出码 0。
-   `spec_validator` 还必须提供独立审查报告与 `PASS` 证明。

### 11.3 Reference Verification

-   每条引用应提供 DOI 或 arXiv ID。
-   离线模式只检查标识符格式，结果为 `INCOMPLETE`，不能视为已核验。
-   在线模式会访问 Crossref / arXiv 公共接口核验记录。

``` bash
st2 audit --manifest research/audit/manifest.json --online
```

在线核验需要网络权限。

### 11.4 Method-Code Alignment

-   将论文中的重要方法主张映射到论文小节、代码路径和实验/证据路径。
-   路径存在性只证明可追踪性，不证明论文和代码语义一致。
-   `method_code_auditor` 必须提供独立审计报告和 `PASS` 证明。

### 11.5 Agent Attestations

Manifest 中必须配置以下三份报告：

-   `research/audit/spec-validator.md`
-   `research/audit/reference-verifier.md`
-   `research/audit/method-code-auditor.md`

由对应 Agent 完成真实检查后，才可以将相应状态设为
`PASS`。不能仅因为文件存在就声称审计通过。

### 11.6 执行审计

``` bash
st2 audit --manifest research/audit/manifest.json
```

在线核验 DOI / arXiv：

``` bash
st2 audit --manifest research/audit/manifest.json --online
```

审计报告写入：

``` text
research/audit/audit-report.json
```

状态说明：

-   `PASS`：该检查已通过。
-   `FAIL`：检查发现错误或不一致。
-   `INCOMPLETE`：缺少配置、证据、在线核验或 Agent 证明。

只有四项检查全部 `PASS`，总结果才是 `PASS`。结构化 CLI
检查不能代替专家判断或人工审阅。

------------------------------------------------------------------------

## 12. 目录与产物说明

``` text
scientisttwo-codex-full/
├── AGENTS.md                       # PI 全局指令
├── .codex/
│   ├── config.toml                 # Codex 项目配置
│   └── agents/                     # 27 个专业 Agent
├── .agents/skills/scientisttwo/
│   └── SKILL.md                    # 完整科研工作流
├── research/
│   ├── problem.md                  # 研究问题合同
│   ├── budget.toml                 # 迭代与资源预算
│   ├── state.json                  # 当前科研状态
│   ├── ledger/events.jsonl         # 不可覆盖的事件追加记录
│   ├── literature/                 # 文献与局限证据
│   ├── candidates/                 # 候选假设
│   ├── experiments/                # 每次实验的独立运行目录
│   ├── ablations/                   # 消融计划与结果
│   ├── reviews/                     # 审稿与答辩记录
│   └── audit/                       # Manifest、审计报告与证明
├── scripts/                        # 示例实验与项目自定义脚本
├── src/scientisttwo/               # Python 状态机、CLI、运行器、审计器
├── tests/                           # 单元测试
└── paper/
    ├── main.tex                     # LaTeX 论文骨架
    └── references.bib               # BibTeX 文献库
```

建议将每轮实验的关键产物与 Git Commit
对应起来。数据集、权重和受限文件是否纳入版本控制，应按许可证和机构政策决定。

------------------------------------------------------------------------

## 13. 并行协作与安全建议

1.  **限制并发**：默认配置为每个会话最多 8 个 Agent
    线程；根据模型额度、内存和 GPU 资源调整。
2.  **单 Worktree 单写入者**：一个 Worktree 同一时间只允许一个代码 Agent
    修改。
3.  **独立 Critic**：评价 Agent 应基于日志和指标，不应只接受实现 Agent
    的口头结论。
4.  **保护 Baseline**：保留固定 Commit、环境、数据划分和评测协议。
5.  **控制高成本实验**：完整 Benchmark 和云端资源消费必须经过人工审批。
6.  **保留失败记录**：失败候选和负结果是 Idea Evolution
    的输入，不应删除。
7.  **保护凭据**：使用环境变量或安全凭据管理，不将 Secret 写入
    Git、Prompt 或日志。
8.  **遵守数据许可**：不得将私有数据上传给未经批准的模型或外部服务。
9.  **定期备份**：备份
    `research/state.json`、`research/ledger/`、实验目录、Manifest
    和论文版本。

------------------------------------------------------------------------

## 14. 常见问题与恢复

### Q1：`st2: command not found`

确认虚拟环境已激活，并在项目根目录重新执行：

``` bash
python -m pip install -e .
```

也可以用：

``` bash
python -m scientisttwo doctor
```

### Q2：提示找不到项目根目录

必须从包含 `AGENTS.md` 和 `.codex/` 的项目根目录执行命令。

### Q3：`st2 init` 提示 State is already initialized

这是防止意外覆盖研究状态的保护。先备份整个
`research/`，再建立新的项目副本；不要直接清空历史记录。

### Q4：实验结束但提示缺少 metrics.json

确认训练脚本读取了环境变量 `ST2_METRICS_PATH`，并在该路径写入合法 JSON
对象。检查对应运行目录中的 `stdout.log` 和 `stderr.log`。

### Q5：实验命令中的 `&&` 或管道不起作用

运行器不经过 Shell。将复杂命令写进 `.py` 或 `.sh` 脚本，再运行脚本。

### Q6：Agent 或 Skill 没有加载

确认在 Codex App 打开项目根目录，检查 `.codex/agents/*.toml` 与
`.agents/skills/scientisttwo/SKILL.md`，然后重新打开项目。

### Q7：审计结果是 `INCOMPLETE`

检查 Manifest 是否填全、重放命令是否成功、DOI / arXiv
是否在线核验，以及三个审计 Agent 是否生成报告并提供 `PASS` 证明。

### Q8：如何恢复中断的研究？

重新打开同一项目，在终端执行：

``` bash
st2 status
```

然后在 Codex 主线程中要求它先读取
`research/state.json`、`research/ledger/events.jsonl`
和最近实验目录，从当前阶段继续。不要重新初始化状态。

------------------------------------------------------------------------

## 15. 能力边界

-   本项目复现的是公开论文所描述的科研工作流，不是 Google
    私有实现的逐行复制。
-   Codex Agent 的实际调用、并行调度和推理由 Codex App 控制；Python CLI
    不会独立创建或调度所有 Agent。
-   `st2 gate`
    负责校验阶段流转和记录决策，但不会判断某个科学结论在学术上是否正确。
-   自动 Peer Review 仅用于诊断和改进，不等于真实会议录用决定。
-   新颖性分数不构成原创性证明；需要通过相关工作检索和专家判断。
-   审计器的路径检查与结构检查不能替代真实实验复现、统计分析和人工审查。
-   研究结果的可靠性仍依赖数据质量、基线实现、计算资源、实验设计和研究者监督。
-   不保证发现新颖成果、超过 SOTA 或获得论文录用。

------------------------------------------------------------------------

## 参考

-   ScientistTwo 公开论文：<https://arxiv.org/abs/2609.19644>
-   Codex 文档：<https://developers.openai.com/codex/>

**推荐首次运行顺序：** 安装 → 填写 `research/problem.md` → 调整
`research/budget.toml` → `st2 doctor` → `st2 init` → `st2 status` → 在
Codex App 输入 `$scientisttwo` → 审核每个阶段证据 → 完成四层审计。
