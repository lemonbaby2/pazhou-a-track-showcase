# 从 0 到 1 的实验日志

> 记录人：李梓鹏 · 设备：DGX Spark `spark-a8d2` · 时间：2026-10-29 → 2026-10-30
> 原则：**失败不删、数字不改、口径不变**。每一次"没跑出结果"都留在表里。

---

## 阶段 0 · 环境搭建（2026-10-29）

| 步骤 | 结果 | 踩的坑 |
|---|---|---|
| 拉 `pollen-robotics/microduck` | OK，~25 个顶层目录 | — |
| 拉 `pollen-robotics/microduck_rl` | OK | DGX 全局 git `insteadOf` 重写到 gitclone.com 慢镜像 → 改用 codeload tarball |
| `uv sync` | OK，`.venv` 落盘 | 首次装完 torch 是 **CPU 轮子**（`cuda.is_available() == False`） |
| 修 torch | 从 `~/isaacsim-venv` 复制 `torch 2.11.0+cu130` + `nvidia/*` 包 | 直接 `uv pip install --index-url .../cu130` 在 aarch64 上反复超时 |
| `list-envs` | 列出官方任务 | `Mjlab-Velocity-Flat-MicroDuck` 是走路，命令 ±0.4 m/s |

**结论**：官方任务只到"走路"，出厂不具备短跑能力。要冲速度必须自定义任务。

---

## 阶段 1 · v1 配方（2026-10-30 02:49 起）

### 设计意图

改三件事：命令区间抬到 **0.8–2.6 m/s**、`air_time` 权重从 3.0 提到 **5.0**（鼓励腾空）、回合缩到 12 s。

### 实测（前 888 轮，被人工终止）

| 指标 | iter 0 | iter 250 | iter 750 |
|---|---:|---:|---:|
| `mean_reward` | −1.05 | 49.36 | ~49 |
| `mean_episode_length` | 24 | **600（顶满）** | 600 |
| `track_lin_vel` 奖励 | 0.018 | 0.45 | 0.36 |
| `air_time` 奖励 | 0.001 | **4.45** | 4.52 |
| 摔倒率 | 高 | ~0.2% | ~0.2% |
| **实测速度（cmd 2.6）** | — | 0.135 | **0.091** |

### 诊断：reward hacking

回合奖励 49 分、回合顶满 600 步、几乎不摔，看起来"训得很好"。
但拆开看：**腾空奖励 4.45 分，速度奖励 0.45 分——10 倍倒挂**。
策略学到的是「站住不动 + 踮脚 + 小跳」，因为这样腾空时间最长、又不会摔。
实测速度 0.09 m/s，**比走路还慢，且越训越慢**（0.135 → 0.091）。

**决策**：终止 v1，归档到 `logs/v1_sprint_archive`，重写配方。不再在 v1 上耗算力。

---

## 阶段 2 · v2 配方（2026-10-30 04:27 起，3000 轮）

### 改动（相对 v1）

| 项 | v1 | v2 | 理由 |
|---|---:|---:|---|
| `track_linear_velocity` | 3.0 | **6.0** | 让速度成为绝对主导 |
| `air_time` | 5.0 | **1.0** | 腾空是速度的**结果**，不是目标 |
| `air_time.command_threshold` | 0.05 | **0.5** | 低速时腾空不给分，堵死"站着跳" |
| `air_time` 门槛区间 | 0.10–0.35 | 0.12–0.30 | 收窄，减少可钻的窗口 |
| `upright` / `pose` | 1.0 / 0.3 | 0.5 / 0.1 | 减半，别把爆发力罚死 |
| `head_pose_tracking` | 0.3 | 0.1 | 短跑不关心脖子 |
| 命令区间 | 0.8–2.6 | **0.3–1.6** | 课程式：先学会跑，再抬上限 |

### 训练过程（3000 轮，9.1 s/iter，8.3 h）

| 指标 | iter 0 | iter 2999 | 变化 |
|---|---:|---:|---|
| `track_lin_vel` | 0.018 | **2.131** | ×118 |
| `mean_reward` | −1.05 | 16.80 | 转正并增长 |
| `mean_episode_length` | 24 | 290.6 | ×12 |
| `error_vel_xy` | 0.0257 | 0.0878 | ↑ 3.4× |
| `error_vel_yaw` | 0.0534 | **0.7120** | **↑ 13.3×（异常）** |
| `air_time_mean` | 0.0504 | 0.0868 | ↑ |
| `slip_velocity_mean` | 0.0918 | 0.0535 | ↓（滑步改善） |

### 关键：检查点同口径扫描

只换检查点，其余条件完全相同（32 环境 × 1200 步，命令 1.6 m/s）：

| 检查点 | 250 | 500 | 1000 | 1500 | 2000 | 2500 | 2999 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 平均速度 (m/s) | **0.4572** | 0.3599 | 0.1872 | 0.1818 | 0.1106 | 待补 | 0.1321 |
| 相对最佳 | 100% | 78.7% | 41.0% | 39.8% | 24.2% | — | 28.9% |

**最佳在 iter 250，之后单调退化。** 与训练侧 `error_vel_yaw` 从 0.05 涨到 0.71 完全对应：策略学会了"扭着跑"，速度掉、偏航失控。

---

## 阶段 3 · 结论

1. **奖励结构决定行为，不是奖励总量。** v1 奖励 49 分但速度 0.09；v2 奖励 16.8 但速度 0.457。**回合奖励不能当性能指标。**
2. **腾空类奖励天然可被 hack。** 唯一的解法是把它挂在速度条件上（`command_threshold=0.5`），而不是简单降权。
3. **存在"最优训练步数"，早停是必需动作。** 本任务 250 轮到顶，3000 轮反而退化 71%。调参若不做中途评测，一定把最好的一版训没。
4. **命令覆盖 = 速度上限。** 把命令给到 2.6（超出训练分布 1.6），速度从 0.457 掉到 0.180。不是策略不努力，是它没见过。

---

## 阶段 4 · 未完成（诚实的欠账）

| 项 | 状态 |
|---|---|
| 复现 2.07 m/s | ❌ 未做到。最佳 0.457 平均 / 0.934 单帧峰值 |
| 环境数 512 → 13500 轮（对齐公开方案） | ❌ 未跑。当前 4096 环境 × 3000 轮 |
| 命令课程继续抬到 2.6 并重训 | ❌ 未做（下一轮实验的首选项） |
| 早停策略（按实测速度选 ckpt） | ⚠️ 已手工验证，未自动化进训练脚本 |
| 真机 sim2real | ❌ 未做 |
| ONNX 导出 | ❌ 未做 |

---

## 附：命令留档

```bash
# v1
MUJOCO_GL=egl .venv/bin/train Mjlab-Sprint-Flat-MicroDuck \
  --env.scene.num-envs 4096 --agent.max-iterations 5000 \
  --agent.run-name duck_sprint --agent.logger tensorboard \
  --agent.save-interval 250 --video True --video-length 300 --video-interval 250

# v2
MUJOCO_GL=egl .venv/bin/train Mjlab-SprintV2-Flat-MicroDuck \
  --env.scene.num-envs 4096 --agent.max-iterations 3000 \
  --agent.run-name duck_sprint_v2 --agent.logger tensorboard \
  --agent.save-interval 250 --video True --video-length 300 --video-interval 250

# 测速
.venv/bin/python probe_sprint_speed.py --ckpt <run>/model_250.pt \
  --task Mjlab-SprintV2-Flat-MicroDuck --cmd 1.6 --steps 1200 --num-envs 32 -o out.json
```
