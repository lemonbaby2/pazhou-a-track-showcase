# MicroDuck 实验事实档案

所有条目都能回溯到 DGX（spark-a8d2 / 192.168.1.217）上的具体文件。

## 平台

- 机器：NVIDIA DGX Spark，GB10，aarch64，121 GB 统一内存，CUDA sm_121
- 训练栈：`/home/nvidia/duck-rl`（官方 `pollen-robotics/microduck_rl`，mjlab 1.3.0 + warp-lang 1.12.0）
- torch：2.11.0+cu130（PyPI aarch64 只有 CPU 版，从 `~/isaacsim-venv` 复制 CUDA 版解决）
- 注册任务：45 个官方 + 2 个本文新增（Sprint v1 / v2）

## 新增任务与代码

- `src/mjlab_microduck/tasks/microduck_sprint_env_cfg.py`：本文新增，不改官方文件
- 注册名：`Mjlab-Sprint-Flat-MicroDuck`（v1）、`Mjlab-SprintV2-Flat-MicroDuck`（v2）
- 工具：`export_sprint_metrics.py`（曲线导出）、`probe_sprint_speed.py`（独立测速）

## 官方出厂配方（事实）

`Mjlab-Velocity-Flat-MicroDuck`：
- `lin_vel_x = (-0.4, 0.4)`，`lin_vel_y = (-0.3, 0.3)`，`ang_vel_z = (-1.0, 1.0)`
- `rel_heading_envs = 0.0`，回合 20 s
- 奖励：track_linear_velocity 2.0 / air_time 3.0（窗 [0.125,0.300]，阈值 0.01）/ upright 2.0 / pose 1.0

## Sprint v1（已完成 888 迭代，判定为失败实验）

配置：命令 (0.8,2.6)，air_time 权重 5.0、窗 [0.10,0.35]、阈值 0.05，track 3.0，upright 1.0，pose 0.3，回合 12 s。
日志：`logs/rsl_rl/velocity/2026-10-30_02-52-26_duck_sprint`

| 指标 | 初值 | 末值 |
|---|---|---|
| error_vel_xy | 0.0446 | 1.8808 |
| mean_episode_length | 24 | 589.4（上限 600） |
| mean_reward | −0.7865 | 49.3646 |
| air_time 奖励 | 0.0099 | 4.4502 |
| track_lin_vel 奖励 | 0.0070 | 0.4469 |
| air_time_mean (s) | 0.0502 | 0.1642 |
| slip_velocity_mean | 0.0918 | 0.0791 |

实测速度（命令锁死 2.6 m/s，32 环境，1000 步）：

| 检查点 | 平均速度 | 峰值 |
|---|---|---|
| model_250 | 0.1351 m/s | 0.2853 m/s |
| model_750 | 0.0905 m/s | 0.2804 m/s |

**结论：奖励入侵（reward hacking）。** 站立不倒 + 小幅踮脚即可拿到腾空奖励，
回合奖励升高而速度下降；训练更久反而更稳地停在刷分模式。

## Sprint v2（修正配方）

改动：track 6.0；air_time 1.0、阈值 0.5、窗 [0.12,0.30]；upright 0.5；pose 0.1；head_pose_tracking 0.1；
命令改为课程式 (0.3,1.6)。
日志：`logs/rsl_rl/velocity/2026-10-30_04-27-30_duck_sprint_v2`

曲线（第 309 轮）：track_lin_vel 奖励 0.6656（已超 v1 跑满 888 轮的 0.4469），
air_time 奖励 0.0176（v1 为 4.4502，差约两个数量级），
mean_episode_length 116.0（v1 为 589.4），mean_reward 5.8264。

同口径实测（均为第 250 轮检查点，32 环境，1000 步）：

| 测速命令 | 配方 | 平均速度 | P95 | 峰值 |
|---|---|---|---|---|
| 1.6 m/s | v1 | 0.1481 | 0.2058 | 0.2507 |
| 1.6 m/s | v2 | **0.4572** | 0.6988 | **0.9335** |
| 2.6 m/s | v1 | 0.1351 | 0.2085 | 0.2853 |
| 2.6 m/s | v2 | 0.1797 | 0.3264 | 0.5457 |

**结论 1：同迭代数、同命令下，v2 平均速度是 v1 的 3.09 倍（1.6 m/s 命令）。**
**结论 2：命令超出课程上限（2.6 > 1.6）时 v2 速度回落至 0.1797，**
说明策略不会自动外推到未见过的命令区间 —— 命令覆盖决定可达速度上界。

## 公开短跑成绩（外部口径，非本文结果）

- Hannes 1.60 m/s；Max Sumrall 1.88 m/s；电磁波Studio（4090D，13500 迭代，512 环境）2.07 m/s，瞬时 2.20 m/s
- 三方任务、命令空间与测速口径未统一，论文中只作背景参照，不作直接排名。
