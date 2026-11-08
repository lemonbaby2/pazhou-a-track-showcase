# MicroDuck 具身智能技术储备 · 完整归档

> 本目录是 **MicroDuck 机器鸭专题的全量自包含归档**：短跑策略自训、Datawhale 8 本 Notebook 复现、
> Task8 视觉语言导航控制层优化、双栏论文稿与写作知识库、全部执行脚本与原始记录。
>
> **与琶洲 A 赛道的关系**：这里是「移动控制 / 强化学习 / 视觉语言导航」的**能力佐证与技术储备**，
> **不是 A 赛道比赛策略，也不是官方计分结果**。A 赛道用统一轮式人形平台（见根 `README.md` 第 0 节），
> 与 25 cm 双足 MicroDuck 不同构。两套数字不得混用。

---

## 0. 结论先行

| 板块 | 最好的结果 | 最重要的一条负面结论 |
|---|---|---|
| **① 短跑策略（自训 PPO）** | 同口径 **0.1481 → 0.4572 m/s（3.09 倍）**，峰值 0.9335 m/s | **训练到 3000 轮反而退化到 0.1321 m/s**，最佳检查点是 iter 250；`mean_reward` 与实测速度严重脱钩 |
| **② 8 本课程复现** | 10 本 notebook（00–09）全部执行成功，含 17 段实拍 MP4 | Task3/4 日志里有 `Invalid choice`，**9/9 全绿 ≠ 任务真注册成功**；Task5 900 步 **59 次失败重置**；Task6 `getup` 调用 **0 次**；Task7 无 RDK X5 硬件 |
| **③ Task8 导航优化** | 三场景平均残余距离 **1.477 → 1.127 m（改善 21.7%）** | 三场景**仍然全部没走到**；根因是出厂行走策略物理速度上限仅 0.14–0.15 m/s，控制层已穷尽 |
| **④ 论文与知识库** | A4 双栏投稿稿（宋体 / Times New Roman，4 表 5 图 13 式 17 引用） | 定稿于 10-30，**未包含 3000 轮退化那一节** |

**一句话**：这个项目的价值不在「把鸭子跑得多快」，而在**三条可复用的定量诊断**——
奖励失衡会导致 reward hacking、上游命令二值化会让 MPC 失效、`model_stop` 不等于到达。

---

## 1. 三条铁律（读任何数字前先看）

1. **不要跨口径比速度。** 社区公开 2.07 m/s（4090D / 512 环境 / 13500 轮 / 瞬时读数）与本项目 0.457 m/s（32 env × 1200 步 / 命令锁 1.6 m/s / 平均速度）**不是同一个测量**，本文不做跨口径比较，也**没有复现 2.07 m/s**。
2. **不要拿 `mean_reward` 当性能指标。** v2 训练末期回合奖励 16.8，实测速度只有 0.1321 m/s。
3. **不要把「自行训练」和「官方权重复现」混为一谈。** ① 是本项目 PPO 续训 3000 轮；② 只加载官方预训练权重跑闭环，不训练、不连板。混着比会得出错误结论。

---

## 2. 目录地图

```text
microduck/
├── README.md                    ← 本文件：总索引与边界
├── METRICS.md                   全部性能指标汇总（短跑 / 8 本 / Task8 优化）
├── RECOMMENDATIONS.md           历轮全部建议、状态与待决策项
├── MANIFEST.csv                 逐文件清单（路径 / 字节 / SHA-256）
├── README_sprint.md             短跑策略原始主文档（Gitee 主 README 保真迁入）
├── README.en.md                 英文版说明
├── LICENSE                      Apache-2.0（上游 Pollen Robotics）
│
├── src/                         短跑任务配置 v1/v2 + 上游快照 + 注册补丁
├── scripts/                     测速 / 指标导出 / 生图 / 论文构建 / 训练队列
├── data/                        13 份性能 JSON（v1/v2 曲线、7 检查点扫描、测速）
├── figs/                        fig2–fig7 共 6 张论文图
├── checkpoints/                 model_250.pt（最佳）+ model_2999.pt（退化证据）
├── videos/                      60 s 合辑 + 10 段片段 + 144 段全量 zip + v1 13 段
├── docs/                        硬件 BOM / 测速协议 / 训练日志 / 写作风格指南
├── papers/                      双栏投稿稿 docx
│
├── course/                      Datawhale 8 本 Notebook 复现
│   ├── Task1-8_学习心得全集.md   8 篇逐本心得（约 1.2 万字）
│   ├── README.md                 课程索引 + 三平台位置对照
│   ├── notebooks/                00–09 共 10 本执行后 ipynb（含输出）
│   ├── validation/               15 份验收 JSON + 10 份执行记录
│   ├── videos/                   17 段课程实拍 MP4
│   ├── logs/                     10 本原始运行 .log（含 invalid choice 证据）
│   ├── optimization/             ★ Task8 控制层优化：报告 / 脚本 / 18 组数据 / 6 段视频
│   ├── site_src/                 课程站点源码（app.py / index.html / duck/ / runs.db）
│   └── upstream-docs/            课程原始说明 + task1/task2 原件与笔记
│
├── paper-agent/                 写论文 agent：知识库 + 实验日志 + 脚本 + docx 成品
└── tooling/                     全部工具脚本
    ├── lesson-scripts/           执行 / 修补 / 录制 / 探测脚本（53 个）
    └── lightnav-probe/           LightNav 上游脚本、优化脚本、18 组原始报告
```

**体积**：362 文件 / 144.29 MB（逐文件清单见 [`MANIFEST.csv`](MANIFEST.csv)，含 SHA-256）。
其中单个最大 26.4 MB（144 段训练录像 zip）；`course/` 94.36 MB 是主要占用。
不需要媒体的话可只取文档与 `data/`；仓库本身不含任何需要联网下载的资源。

---

## 3. 快速定位

| 我想找… | 去这里 |
|---|---|
| 短跑所有数字与结论 | [`README_sprint.md`](README_sprint.md) · [`METRICS.md`](METRICS.md) |
| 短跑怎么复现 | [`README_sprint.md`](README_sprint.md) 第 7 节 · [`scripts/setup_duckrl.sh`](scripts/setup_duckrl.sh) |
| 8 本心得 / 飞书打卡材料 | [`course/Task1-8_学习心得全集.md`](course/Task1-8_学习心得全集.md) |
| 8 本真实执行指标 | [`course/validation/`](course/validation/) · [`course/logs/`](course/logs/) |
| Task8 优化诊断与 18 组数据 | [`course/optimization/README.md`](course/optimization/README.md) |
| 控制层优化脚本 | [`course/optimization/lightnav_opt.py`](course/optimization/lightnav_opt.py) |
| 硬件清单 / BOM | [`docs/HARDWARE_BOM.md`](docs/HARDWARE_BOM.md) |
| 测速口径定义 | [`docs/METRICS_PROTOCOL.md`](docs/METRICS_PROTOCOL.md) |
| 双栏论文 Word | [`papers/`](papers/) · 生成脚本 [`paper-agent/build_paper.py`](paper-agent/build_paper.py) |
| 写作知识库 / 风格指南 | [`paper-agent/knowledge/`](paper-agent/knowledge/) |
| 还有哪些建议没做 | [`RECOMMENDATIONS.md`](RECOMMENDATIONS.md) |
| 每个文件从哪来、校验和 | [`MANIFEST.csv`](MANIFEST.csv) |

---

## 4. 数据链路与来源

| 阶段 | 平台 | 产物 |
|---|---|---|
| 训练 | DGX Spark `spark-a8d2`（GB10 / aarch64 / 121 GB 统一内存 / CUDA 13.0） | TensorBoard → `data/*.json`，检查点 → `checkpoints/` |
| 评测 | 同上，MuJoCo Warp + `MUJOCO_GL=egl` | `scripts/probe_sprint_speed.py` → 32 env × 1200 步 |
| 课程复现 | 同上 `~/microduck-course-run`，`envs/notebook` | `course/validation/` · `course/videos/` · `course/logs/` |
| Task8 优化 | 同上，模型服务 8050 端口，LightNav-0 官方权重 | `course/optimization/reports/`（18 组） |
| 成文 / 归档 | Windows 本机（RTX 3050 Ti 4 GB，只做文档与绘图） | `paper-agent/` · `papers/` |

**所有指标都来自真实运行落盘的 JSON / trace，不是事后估计。** 完整执行环境见
[`course/README.md`](course/README.md) 第六节。

---

## 5. 与其他仓库的关系（避免找混）

同一批内容历史上分散在三处，本目录是**唯一的全量自包含副本**：

| 位置 | 内容 | 定位 |
|---|---|---|
| **本目录**（`pazhou-a-track-showcase/microduck`） | 362 文件 / 全部板块 | ✅ 全量归档 + 公开展示入口 |
| Gitee `li-zipeng123/duckf--the-playful-duck` | 194 文件 / 短跑 + 课程 + Task8 优化 | 原始发布仓，**不含** paper-agent 与 tooling 脚本 |
| GitHub `lemonbaby2/-123` · `datawhale_microduck/` | Task1/2 原件（main）+ Task3–8（microduck-task2 分支） | 个人档案杂货仓，已加 Task3–8 定位表 |
| GitHub `lemonbaby2/-123` · `embodied-ai/` | 33 篇脱敏对话 + 简历 + 论文 | 具身智能对话档案，与本目录不同用途 |

公开展示页：[`site/microduck.html`](../site/microduck.html)（GitHub Pages 部署后可从 A 赛道展示站进入）。

---

## 6. 诚实边界

1. **没有真机验证**，全部结论来自 MuJoCo / MuJoCo Warp 仿真。
2. **2.07 m/s 未复现**，本项目最好平均速度 0.4572 m/s，且只在本仓测速协议内成立。
3. **Task8 三场景仍未到达目标**，最优残余 0.783–1.651 m；`target_xy` 只用于事后测量，全程未进入控制回路。
4. **Task7 的 BPU 板端部分未做**（无 RDK X5 硬件），记录为 `bpu: not_run_no_board`。
5. **Task8 优化单场景单组运行**，没有多种子重复，21.7% 应按趋势看，不宜当作精确估计。
6. **论文稿定稿于 2026-10-30**，未包含后续 3000 轮退化实验与 Task8 优化；需要并入须重跑 `paper-agent/build_paper.py`。
7. **BOM 是配置清单与估算**，不是采购凭证；详见 [`docs/HARDWARE_BOM.md`](docs/HARDWARE_BOM.md) 边界说明。
8. 本目录**不含个人简历、联系方式、脱敏对话**，隐私材料留在原档案仓。

---

## 7. 许可

- 上游 `microduck_rl` / LightNav-0 / Datawhale 课程材料各遵循其原协议；[`LICENSE`](LICENSE) 为 Apache-2.0 原文。
- 本项目自行编写的脚本、配置、文档与数据可自由用于学习与复现，引用请注明来源仓库。
- 论文稿为未投稿草稿，不得当作已发表成果。
