"""生成检查点退化曲线 fig7（数据来自 data/ 下各 sweep_*.json 与 v2_speed*.json）。"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
FIGS = BASE / "figs"
FIGS.mkdir(exist_ok=True)

# iter -> 平均速度（同口径：32 env × 1200 步，命令 1.6 m/s）
POINTS = {
    250: "v2_speed.json",
    500: "sweep_500.json",
    1000: "sweep_1000.json",
    1500: "sweep_1500.json",
    2000: "sweep_2000.json",
    2500: "sweep_2500.json",
    2999: "v2_speed_final_c16.json",
}


def load(name: str):
    p = DATA / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    xs, mean, p95, peak = [], [], [], []
    for it, fn in sorted(POINTS.items()):
        d = load(fn)
        if not d:
            continue
        xs.append(it)
        mean.append(d["forward_speed_mean_mps"])
        p95.append(d["forward_speed_p95_mps"])
        peak.append(d["forward_speed_peak_frame_mps"])

    fig, ax = plt.subplots(figsize=(5.2, 3.0), dpi=200)
    ax.plot(xs, peak, "o--", color="#9ec5fe", lw=1.2, ms=4, label="单帧峰值")
    ax.plot(xs, p95, "s--", color="#4a90e2", lw=1.2, ms=4, label="P95")
    ax.plot(xs, mean, "o-", color="#c0392b", lw=2.0, ms=6, label="平均前进速度")

    best_i = mean.index(max(mean))
    ax.annotate(
        f"最佳 {mean[best_i]:.3f} m/s @ iter {xs[best_i]}",
        xy=(xs[best_i], mean[best_i]),
        xytext=(xs[best_i] + 260, mean[best_i] + 0.09),
        fontsize=7.5,
        color="#c0392b",
        arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.9),
    )
    ax.annotate(
        f"末期 {mean[-1]:.3f} m/s @ iter {xs[-1]}",
        xy=(xs[-1], mean[-1]),
        xytext=(xs[-1] - 1500, mean[-1] + 0.16),
        fontsize=7.5,
        color="#555",
        arrowprops=dict(arrowstyle="->", color="#777", lw=0.8),
    )

    ax.set_xlabel("训练迭代（PPO iteration）", fontsize=9)
    ax.set_ylabel("前向速度 / (m·s$^{-1}$)", fontsize=9)
    ax.set_title("同一策略在不同检查点的实测速度：越训越慢", fontsize=10)
    ax.set_ylim(0, max(peak) * 1.18)
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    out = FIGS / "fig7_checkpoint_decay.png"
    fig.savefig(out, dpi=200)
    print(f"wrote {out}")
    for it, m in zip(xs, mean):
        print(f"  iter {it:>5}  mean={m:.4f}")


if __name__ == "__main__":
    main()
