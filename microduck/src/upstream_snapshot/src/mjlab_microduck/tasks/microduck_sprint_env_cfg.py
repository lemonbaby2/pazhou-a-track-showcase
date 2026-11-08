"""MicroDuck Sprint —— 面向 >2 m/s 冲刺的 PPO 环境配置.

设计来源：官方 `Mjlab-Velocity-Flat-MicroDuck`（出厂 lin_vel_x 只有 ±0.4 m/s，
那只是"走路"）。要跑出 2 m/s 量级的短跑，必须改三件事：

  1. 速度命令范围抬高（(0.8, speed_max)），并把 heading 收窄 → 强制直行。
  2. 奖励配方重排：速度追踪加倍、air_time（双脚腾空）权重上调且放宽时间窗；
     头部姿态追踪降权（短跑不关心脖子），foot_slip / action_rate 保留作"动作变形"惩罚。
  3. 回合缩短到 12 s —— 冲速度靠的是高频冲刺片段，长回合只会稀释梯度。

本文件不改动官方任何文件，纯配置派生。
"""

from __future__ import annotations

from copy import deepcopy

from mjlab.envs import ManagerBasedRlEnvCfg  # noqa: F401  (typing only)

from .microduck_velocity_env_cfg import (
    MicroduckRlCfg,
    make_microduck_velocity_env_cfg,
)


def make_microduck_sprint_env_cfg(
    play: bool = False,
    speed_max: float = 2.6,
    speed_min: float = 0.8,
    straight_only: bool = True,
    preset: str = "v1",
) -> "ManagerBasedRlEnvCfg":
    """冲刺任务：只往前跑，越快越好，鼓励腾空。

    preset="v1"：第一版配方（已被实测证明会 reward hacking —— 站着刷腾空分）。
    preset="v2"：修正版。把速度追踪提为绝对主导、腾空奖励降权并抬高触发门槛、
                 速度命令先收窄到可学区间（课程式），姿态类奖励减半。
    """
    cfg = make_microduck_velocity_env_cfg(play=play)

    # ---------- 1. 命令：往前推，不许横向漂 ----------
    twist = cfg.commands["twist"]
    twist.ranges.lin_vel_x = (float(speed_min), float(speed_max))
    twist.ranges.lin_vel_y = (-0.12, 0.12)
    twist.ranges.ang_vel_z = (-0.25, 0.25)
    if straight_only:
        # 全体采样相对朝向，且朝向偏差收窄 → 跑偏即被奖励函数惩罚
        twist.rel_heading_envs = 1.0
        twist.ranges.heading = (-0.12, 0.12)

    # ---------- 2. 奖励配方 ----------
    r = cfg.rewards
    # 速度追踪（正）
    r["track_linear_velocity"].weight = 3.0
    r["track_angular_velocity"].weight = 1.0
    # 腾空（正）—— 官方 3.0 / [0.125, 0.300]，冲刺放宽到 [0.10, 0.35]
    r["air_time"].weight = 5.0
    r["air_time"].params["threshold_min"] = 0.10
    r["air_time"].params["threshold_max"] = 0.35
    r["air_time"].params["command_threshold"] = 0.05
    # 姿态（保跑姿不乱）
    r["upright"].weight = 1.0
    r["pose"].weight = 0.3
    # 动作变形 / 打滑 / 跑偏（负）
    r["action_rate_l2"].weight = -0.05          # 放宽，别把冲刺的爆发力罚死
    r["foot_slip"].weight = -0.35                # 加重：滑步=假速度
    r["foot_clearance"].weight = -1.0
    r["foot_swing_height"].weight = -0.25
    r["body_ang_vel"].weight = -0.03
    # 头部姿态：短跑降权（官方 2.0，那是"边跑边看"的任务）
    r["head_pose_tracking"].weight = 0.3
    r["body_pose_tracking"].weight = 0.0

    # ---------- 3. 回合长度 ----------
    cfg.episode_length_s = 12.0

    if preset == "v2":
        # v1 实测（DGX，iter 250/750，命令锁死 2.6 m/s）：
        #   mean 0.135 → 0.091 m/s，回合长度顶满 600 步、摔倒率 0.2%，
        #   air_time 奖励 4.52 而 track_linear_velocity 只有 0.36
        #   ⇒ 策略选择"站住不倒 + 踮脚刷腾空"，是典型 reward hacking。
        # v2 把奖励结构倒过来：速度追踪一家独大，腾空只在高速命令下才给分。
        twist.ranges.lin_vel_x = (0.3, 1.6)     # 先学会跑，再往上抬（课程）
        r["track_linear_velocity"].weight = 6.0
        r["air_time"].weight = 1.0
        r["air_time"].params["command_threshold"] = 0.5
        r["air_time"].params["threshold_min"] = 0.12
        r["air_time"].params["threshold_max"] = 0.30
        r["upright"].weight = 0.5
        r["pose"].weight = 0.1
        r["head_pose_tracking"].weight = 0.1

    return cfg


__all__ = ["make_microduck_sprint_env_cfg", "MicroduckRlCfg"]
