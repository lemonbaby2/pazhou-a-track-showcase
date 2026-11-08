#!/usr/bin/env python3
"""Headless 测速：加载 MicroDuck 冲刺策略 checkpoint，实测前进速度（m/s）。

复用 mjlab 的 env + rsl_rl runner，不开 viewer，纯 CUDA 批量跑。
命令被强制固定到给定值（默认 2.6 m/s），记录 trunk 前向线速度。

用法:
    .venv/bin/python probe_sprint_speed.py --ckpt logs/rsl_rl/velocity/<run>/model_1000.pt \
        --task Mjlab-Sprint-Flat-MicroDuck --cmd 2.6 --steps 1500 --num-envs 64
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import torch

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--task", default="Mjlab-Sprint-Flat-MicroDuck")
    ap.add_argument("--cmd", type=float, default=2.6, help="forced forward speed command m/s")
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--num-envs", type=int, default=64)
    ap.add_argument("--warmup", type=int, default=100, help="steps ignored before stats")
    ap.add_argument("-o", "--out", default="sprint_speed.json")
    args = ap.parse_args()

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    env_cfg = load_env_cfg(args.task, play=True)
    env_cfg.scene.num_envs = args.num_envs
    agent_cfg = load_rl_cfg(args.task)

    env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
    env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)

    runner_cls = load_runner_cls(args.task) or MjlabOnPolicyRunner
    runner = runner_cls(env, asdict(agent_cfg), device=device)
    runner.load(args.ckpt, load_cfg={"actor": True}, strict=True, map_location=device)
    policy = runner.get_inference_policy(device=device)

    unwrapped = env.unwrapped
    twist = unwrapped.command_manager.get_term("twist")
    robot = unwrapped.scene["robot"]

    n = args.num_envs
    forced = torch.zeros(n, 3, device=device)
    forced[:, 0] = args.cmd

    obs = env.get_observations()
    samples: list[float] = []
    per_env_max = torch.zeros(n, device=device)

    with torch.no_grad():
        for i in range(args.steps):
            # 命令锁死：每步覆盖（命令管理器会周期性重采样）
            twist.command[:] = forced
            actions = policy(obs)
            obs, _rew, dones, _infos = env.step(actions)
            if bool(dones.any()):
                obs = env.get_observations()
            v = robot.data.root_link_lin_vel_b[:, 0].detach().float()
            if i >= args.warmup:
                samples.append(v.mean().item())
                per_env_max = torch.maximum(per_env_max, v)

    import statistics as st

    vals = samples or [0.0]
    peak_frame = max(vals)
    peak_env = per_env_max.max().item()
    payload = {
        "checkpoint": str(Path(args.ckpt).name),
        "task": args.task,
        "cmd_mps": args.cmd,
        "steps": args.steps,
        "num_envs": n,
        "forward_speed_mean_mps": round(st.mean(vals), 4),
        "forward_speed_median_mps": round(st.median(vals), 4),
        "forward_speed_p95_mps": round(sorted(vals)[int(0.95 * (len(vals) - 1))], 4),
        "forward_speed_peak_frame_mps": round(peak_frame, 4),
        "forward_speed_peak_env_mps": round(peak_env, 4),
    }
    out = Path(args.out)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
