#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 MicroDuck 论文插图（数据全部来自 DGX 真实训练日志）。

输入：paper-agent/data/v1_metrics.json, v1_speed.json, v2_metrics.json, v2_speed.json
输出：paper-agent/figs/fig2_*.png ... 供 build_paper.py 插入。
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
FIGS = os.path.join(BASE, "figs")
os.makedirs(FIGS, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 9


def load(name):
    p = os.path.join(DATA, name)
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None


def save(fig, name):
    out = os.path.join(FIGS, name)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)


def smooth(v, k=15):
    if len(v) < k:
        return v
    out = []
    for i in range(len(v)):
        a = max(0, i - k + 1)
        out.append(sum(v[a:i + 1]) / (i - a + 1))
    return out


def main():
    v1 = load("v1_metrics.json")
    v2 = load("v2_metrics.json")

    # ---- 图2：v1 训练过程（速度误差 / 回合长度 / 回合奖励）----
    if v1:
        it = v1["iters"]
        s = v1["series"]
        fig, axes = plt.subplots(1, 3, figsize=(10.2, 2.7))
        axes[0].plot(it, s["error_vel_xy"], color="#c0392b", lw=1.0, alpha=.35)
        axes[0].plot(it, smooth(s["error_vel_xy"]), color="#c0392b", lw=1.6)
        axes[0].set_title("(a) 速度追踪误差 error_vel_xy")
        axes[0].set_xlabel("迭代次数")
        axes[0].set_ylabel("误差 / (m·s$^{-1}$)")
        axes[1].plot(it, s["mean_episode_length"], color="#1f77b4", lw=1.0, alpha=.35)
        axes[1].plot(it, smooth(s["mean_episode_length"]), color="#1f77b4", lw=1.6)
        axes[1].axhline(600, ls="--", c="gray", lw=.8)
        axes[1].set_title("(b) 平均回合长度")
        axes[1].set_xlabel("迭代次数")
        axes[1].set_ylabel("步数（600 = 回合上限）")
        axes[2].plot(it, s["mean_reward"], color="#2c8a4b", lw=1.0, alpha=.35)
        axes[2].plot(it, smooth(s["mean_reward"]), color="#2c8a4b", lw=1.6)
        axes[2].set_title("(c) 平均回合奖励")
        axes[2].set_xlabel("迭代次数")
        axes[2].set_ylabel("奖励")
        for a in axes:
            a.grid(alpha=.25, lw=.5)
        save(fig, "fig2_v1_training.png")

    # ---- 图3：奖励结构失衡（v1 的证据）----
    if v1:
        it = v1["iters"]
        s = v1["series"]
        fig, ax = plt.subplots(figsize=(5.0, 2.9))
        ax.plot(it, smooth(s["air_time_reward"]), label="腾空奖励 air_time", color="#e67e22", lw=1.8)
        ax.plot(it, smooth(s["track_lin_vel"]), label="速度追踪奖励 track_lin_vel", color="#2563eb", lw=1.8)
        ax.set_xlabel("迭代次数")
        ax.set_ylabel("回合内平均奖励")
        ax.set_title("Sprint v1：腾空奖励约为速度追踪奖励的 10 倍")
        ax.legend(frameon=False, fontsize=8)
        ax.grid(alpha=.25, lw=.5)
        save(fig, "fig3_reward_imbalance.png")

    # ---- 图4：v1 / v2 同口径实测速度对比（iter 250，两种命令）----
    s_v1_16 = load("v1_speed_cmd16.json")
    s_v2_16 = load("v2_speed.json")
    s_v1_26 = load("v1_speed.json")
    s_v2_26 = load("v2_speed_cmd26.json")
    if s_v1_16 and s_v2_16:
        groups = []
        if s_v1_26 and s_v2_26:
            groups = [("命令 1.6 m/s", s_v1_16, s_v2_16), ("命令 2.6 m/s", s_v1_26, s_v2_26)]
        else:
            groups = [("命令 1.6 m/s", s_v1_16, s_v2_16)]
        fig, ax = plt.subplots(figsize=(5.2, 2.9))
        x = list(range(len(groups)))
        w = 0.2
        for k, (metric, label, color) in enumerate((
                ("forward_speed_mean_mps", "平均速度", "#2563eb"),
                ("forward_speed_peak_frame_mps", "峰值速度", "#93c5fd"))):
            for j, (gname, a, b) in enumerate(groups):
                ax.bar([x[j] - 0.22 + k * 0.44 - w / 2], [a[metric]], width=w,
                       color="#c0392b" if k == 0 else "#f2b8ae",
                       label="v1 " + label if j == 0 else None)
                ax.bar([x[j] - 0.22 + k * 0.44 + w / 2], [b[metric]], width=w,
                       color=color, label="v2 " + label if j == 0 else None)
        ax.set_xticks(x)
        ax.set_xticklabels([g[0] for g in groups])
        ax.set_ylabel("前进速度 / (m·s$^{-1}$)")
        ax.set_title("同迭代数（250）下同口径实测速度对比")
        ax.legend(frameon=False, fontsize=7, ncol=2)
        ax.grid(axis="y", alpha=.25, lw=.5)
        save(fig, "fig4_speed_compare.png")

    # ---- 图5：公开短跑成绩对标 ----
    pub = [("Hannes", 1.60), ("Max Sumrall", 1.88), ("电磁波Studio（4090D）", 2.07)]
    v2s = load("v2_speed.json")
    if v2s:
        pub.append(("本文 v2（第 250 轮）", v2s["forward_speed_peak_frame_mps"]))
    fig, ax = plt.subplots(figsize=(5.0, 2.6))
    names = [p[0] for p in pub]
    vals = [p[1] for p in pub]
    colors = ["#94a3b8"] * (len(pub) - (1 if v2s else 0)) + (["#2563eb"] if v2s else [])
    ax.barh(names, vals, color=colors)
    for i, v in enumerate(vals):
        ax.text(v + .02, i, f"{v:.2f}", va="center", fontsize=8)
    ax.set_xlabel("峰值前进速度 / (m·s$^{-1}$)")
    ax.set_title("公开短跑成绩与本文结果")
    ax.grid(axis="x", alpha=.25, lw=.5)
    save(fig, "fig5_public_benchmark.png")

    # ---- 图6：v1 与 v2 的训练曲线对照（若 v2 已有数据）----
    if v1 and v2:
        fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7))
        for tag, m, c in (("v1", v1, "#c0392b"), ("v2", v2, "#2563eb")):
            axes[0].plot(m["iters"], smooth(m["series"]["error_vel_xy"]), label=tag, color=c, lw=1.6)
            axes[1].plot(m["iters"], smooth(m["series"]["mean_episode_length"]), label=tag, color=c, lw=1.6)
        axes[0].set_title("(a) 速度追踪误差")
        axes[1].set_title("(b) 平均回合长度")
        for a in axes:
            a.set_xlabel("迭代次数")
            a.legend(frameon=False, fontsize=8)
            a.grid(alpha=.25, lw=.5)
        save(fig, "fig6_v1_v2_curves.png")


if __name__ == "__main__":
    main()
