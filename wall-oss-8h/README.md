# Wall-OSS-0.5 · 8 小时 LIBERO 微调 · 全量归档（含失败复盘）

> **状态：训练中断，未成功完成。** 失败时间 `2026-11-12 13:21:33`，停在 **Step 2008 / 4000**。
> 本目录是 DGX `spark-a8d2` 上 `/home/nvidia/runs/` 的**只读镜像**，用于复盘，不是成果展示。
> **本次归档未重启训练、未修改 DGX 任何配置或进程。**

- **状态页**：<https://lemonbaby2.github.io/pazhou-a-track-showcase/wall-oss-8h.html>（含 loss 曲线与崩溃链路）
- **姊妹实验**：[π0.5 8h 消融（已成功完成）](../vla-8h/README.md) · <https://lemonbaby2.github.io/pazhou-a-track-showcase/vla-8h.html>
- **归档时间**：2026-11-12 15:1x (GMT+8)，共 14 文件 / 约 2.06 MB
- **数据来源**：`nvidia@192.168.1.217:/home/nvidia/runs/` + 本机 `C:/Users/lzp/duck-opt/walloss_*.py`

---

## 1. 这是哪个模型，为什么要训

| 项 | 值 |
|---|---|
| 模型 | **Wall-OSS-0.5**（X-Square-Robot，4B，Qwen2.5-VL-3B 底座） |
| 选它的理由 | 官方 README：task-specific fine-tune 后 15 项真机任务平均进度 **60.5%**，超 π0.5 **17.5%**，deployment-ready |
| 代码 | `/home/nvidia/wall-x`（`wall_x/trainer/fsdp_trainer/train_fsdp.py`） |
| 环境 | `/home/nvidia/wallx-env`（Python 3.10.20 / torch 2.10.0+cu130） |
| 权重 | `/home/nvidia/models/wall-oss-0.5`（7.8 G），`resume_from` 直接指向 `model.safetensors` |
| 数据 | LIBERO，`/home/nvidia/datasets/libero_all` |
| 配置 | `config/walloss_8h.yml`：4000 步、batch 1 × grad_accum 8、lr 5e-5 cosine、BF16、`save_interval: 4000` |
| 冒烟 | 20 步 EXIT=0，loss 0.016–0.34，通过后才起正式训练 |

> 这不是 π0.5 消融的延续，是**换了模型骨干的另一条实验线**。两边数字不得混用。

## 2. 结果：跑了一半，NaN 打断

| 指标 | 值 |
|---|---|
| 完成步数 | **2008 / 4000（50.2%）** |
| flow_loss 首 → 末 | 0.4135 → **0.00863** |
| 最小 / 最大 / 均值 | 0.000050 / 0.651253 / 0.095778 |
| 有效采样点 | **2009** 条（`reports/loss_series.json`） |
| checkpoint | **无**（`save_interval: 4000` 只在终点存；`walloss_8h/` 下仅 1 个 `rank_0.log`） |
| 训练进程 / GPU | 0 个 / 0%（已停摆，日志停在 13:21） |

### 崩溃链路（日志行号可复核）

| 日志 | 内容 |
|---|---|
| `walloss_8h.log:4081` | `13:21:18,648 [FSDP Train] Step 2008: flow_loss 0.008633, grad_norm 1.276` — 最后一个正常反向步 |
| `:4082` | `13:21:18,774 WARNING - Warning: nan in loss at epoch: 0, step: 16072` — **根因** |
| `:4083` | `Training failed with error: element 0 of tensors does not require grad and does not have a grad_fn` |
| `:4092` | `fsdp_trainer.py:163 self.backward() → loss.backward()` 抛 `RuntimeError` |
| `:4118` | `ChildFailedError ... exitcode: 1 (pid 2173448)`，torchrun 终止 |
| `:4148` | `[2026-11-12T13:21:37+08:00] 8H TRAIN EXIT=0` — **shell 包装层退出码，误导项，不代表训练成功** |

### 根因判断

报错文字 `"does not require grad"` 容易被误读成「参数被冻结 / requires_grad 配错」，
但 **grad_norm 前 2008 步一直正常（末步 1.276）**，梯度链路本来是通的。
真正的触发点是紧邻的 `nan in loss`：BF16 + `lr 5e-5` cosine + flow loss 长跑后数值溢出，
scaler 产出非有限标量、autograd 图断开，才在 `backward()` 抛出该错误。
辅助嫌疑：`ar_loss_weight: 0.01` 与 flow loss 量级悬殊、`libero_norm_stats.json` 若有极端分位数。

## 3. 重启前必须改的四项（否则原地再崩）

```text
1. 降学习率      learning_rate: 5.0e-05 → 2.5e-05（或 1.0e-05）
2. 缩短存盘间隔  save_interval / epoch_save_interval: 4000 → 500
                （单份约 8 G，磁盘仅剩 80 G → 只保留最近 2 份）
3. NaN 保护      训练循环加 torch.isfinite(loss) 判断，非有限则 skip 该步并降级 lr
4. 数值核查      检查 libero_norm_stats.json 的 min/max 是否有 inf/极端值；
                BF16 下 optimizer eps 从 1e-8 提到 1e-6
```

**资源前提（重启前先确认）**：系统盘 3.7 T 已用 **98%（剩 80 G）**；
今晨 SOP 全量备份包约 **651 G** 仍占在系统盘（待转移 WD）；
CVAT 19 容器、4 路 SOP 推理服务、nuclio 4 函数均在生产运行。
重启须沿用 `nice` / `taskset` 让出 CPU 给产线，并保留监控的内存保护阈值。

> 2008 步没有 checkpoint，**无法从中断点续跑**，只能改完配置从头开始。

## 4. 目录结构

```
wall-oss-8h/
├── README.md                      本文件（状态 / 根因 / 修复方案 / 边界）
├── config/
│   ├── walloss_8h.yml             正式训练配置（4000 步）
│   ├── walloss_smoke.yml          20 步冒烟配置
│   └── libero_norm_stats.json     归一化统计量（NaN 嫌疑核查对象）
├── logs/
│   ├── walloss_8h.log             正式训练原始日志 1.00 MB（崩溃证据）
│   ├── walloss_smoke.log          冒烟日志
│   └── rank_0.log                 FSDP rank0 日志 1.02 MB
├── reports/
│   ├── loss_series.json           逐条解析的 2009 个 (step, flow_loss, grad_norm)
│   └── summary.json               结构化摘要（status=interrupted / checkpoint_saved=false）
└── scripts/
    ├── run_walloss_8h.sh          DGX 启动脚本
    ├── run_walloss_smoke.sh       冒烟启动脚本
    ├── walloss_setup.py           本机：生成配置
    ├── walloss_launch.py          本机：启动
    ├── walloss_relaunch.py        本机：重启
    └── walloss_watch.py           本机：SSH 查进度（注意它把 shell 的 EXIT=0 当成功，见下）
```

> **`walloss_watch.py` 的已知缺陷**：它用 `grep -c 'EXIT='` 判断训练是否结束，
> 而 `EXIT=0` 是包装脚本打印的，不是 torchrun 的真实退出码 → 会把崩溃误报成「训练结束」。
> 正确判据：查 `ChildFailedError` / `nan in loss` / 是否有 `train_fsdp` 进程。

## 5. 边界声明

- 本目录**不含**模型权重（7.8 G）与任何 checkpoint，全部留在 DGX。
- 训练**未跑完**，loss 数值只能反映前 2008 步趋势，**不得当作最终模型指标或对比结论**。
- 与 A 赛道赛题无关，是具身智能能力储备；不是比赛策略、不是官方计分结果。
- 归档过程为 SFTP 只读拉取 + 本机脚本拷贝，**未终止或修改 DGX 上任何训练进程、监控进程或配置**。
