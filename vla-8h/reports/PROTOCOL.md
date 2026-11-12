# 8 小时连续训练实验协议（pi0.5 3.6B / DGX Spark GB10）

生成时间：2026-11-11 13:25:22
实测冒烟速度：**0.6433 step/s**；总预算 8 h（含 30 min 冒烟），4 个消融臂平分余下 7.5 h。

## 1. 自变量设计（复现论文方法）

| 臂 | 自变量 | 对应论文方法 | 计划步数 | 时长 |
|---|---|---|---:|---:|
| `A_ki` | 基线：Knowledge Insulation + QUANTILES + Beta(1.5,1.0) | pi0.5 原生 flow matching + Knowledge Insulation (arXiv 2505.23705) | 4015 | 112 min |
| `B_lm` | 解冻 VLM 语言模型（仅冻结视觉塔） | Knowledge Insulation 消融（VLM 是否参与训练） | 4015 | 112 min |
| `C_mstd` | QUANTILES -> MEAN_STD | openpi / pi05_libero_finetuned 参考配方 | 4015 | 112 min |
| `D_beta` | Beta(1.5,1.0) -> Beta(1.0,1.0) 均匀时间采样 | pi0 论文 §4 flow matching timestep sampling 消融 | 4015 | 112 min |

共同固定项：`policy.type=pi05`、`pretrained_path=lerobot/pi05_base`、bfloat16、
`gradient_checkpointing=true`、`chunk_size=50`、`n_action_steps=10`、`batch_size=4`、
LIBERO v3.0（1693 episodes / 273465 frames / 40 tasks，本地 1.9 G）、`seed=1000`、
`optimizer_lr=2.5e-5`、`log_freq=50`。

## 2. 已复现的方法

- **Flow matching 动作头**（pi0 / pi0.5 核心）：10 步积分、Beta(1.5,1.0) 时间采样、动作 chunk 50。
- **Knowledge Insulation**（arXiv 2505.23705）：冻结 VLM / 视觉编码器，只训 300 M action expert 与投影。
- **QUANTILES 归一化**（pi0.5 原生）：数据集 `meta/stats.json` 含 q01/q99，STATE/ACTION 走分位数。
- **离散状态输入 + 子任务语言**：`tokenizer_max_length=200`，状态离散化写入 prompt。
- **Timestep sampling 消融**（pi0 论文 §4）：Beta 分布 vs 均匀采样。
- **MEAN_STD 对照**：对齐 openpi / `pi05_libero_finetuned` 参考配方。

## 3. 明确未复现（边界，不得模糊）

| 项 | 原因 |
|---|---|
| pi0.5 论文第一阶段 FAST 离散动作预训练 | openpi / lerobot 仓库只开源第二阶段 flow matching head |
| 部署时高层子任务推理（high-level subtask prediction） | 开源仓库未包含 |
| 论文 60k steps × global batch 384 全量配方 | DGX Spark 单卡 BF16 算力约 21.5 TFLOPS，与 6×A800 差约 90× |
| 原榜单 LIBERO / RoboTwin 数值 | SAPIEN 3.0 仅 x86_64 wheel，aarch64 无法闭环评测 |
| 6B LingBot-VLA / 4B Kairos 全参训练 | 权重在本机但算力不足，仅可做推理级复现（见 `~/vla_repro/REPRODUCTION.md`） |

## 4. 生产保护

训练进程 `nice -n 10` + `taskset -c 0-9`（20 核留一半给产线）。
监控进程每 5 min 检查可用内存与 CVAT / nuclio 容器健康；
可用内存低于 11 GB 时主动终止训练，保住 CVAT 标注与 4 个 YOLO 推理函数。

## 5. 数据真实性

loss / grad norm / lr / step time 全部从 `lerobot_train` 的 tqdm 日志正则解析，
未做任何插值或伪造。原始日志保存在 `logs/train_*.log`，逐条指标在 `reports/metrics.jsonl`。
