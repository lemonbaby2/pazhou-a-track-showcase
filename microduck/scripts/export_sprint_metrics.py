#!/usr/bin/env python3
"""从 mjlab/rsl_rl 的 tensorboard event 文件导出 MicroDuck 冲刺训练曲线 JSON.

用法:
    python export_sprint_metrics.py [run_dir] [-o out.json]

run_dir 缺省时取 logs/rsl_rl/sprint/ 下最新的目录。
输出结构:
    {"run": "...", "iters": [...], "series": {"error_vel_xy": [...], ...}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TAGS = {
    "error_vel_xy": "Metrics/twist/error_vel_xy",
    "error_vel_yaw": "Metrics/twist/error_vel_yaw",
    "air_time_mean": "Metrics/air_time_mean",
    "peak_height_mean": "Metrics/peak_height_mean",
    "slip_velocity_mean": "Metrics/slip_velocity_mean",
    "track_lin_vel": "Episode_Reward/track_linear_velocity",
    "air_time_reward": "Episode_Reward/air_time",
    "mean_reward": "Train/mean_reward",
    "mean_episode_length": "Train/mean_episode_length",
}


def find_latest(root: Path) -> Path:
    cands = [p for p in root.rglob("events.out.tfevents.*")]
    if not cands:
        raise SystemExit(f"no tfevents under {root}")
    return max(cands, key=lambda p: p.stat().st_mtime).parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("-o", "--out", default="sprint_metrics.json")
    ap.add_argument("--root", default=str(Path.home() / "duck-rl" / "logs"))
    args = ap.parse_args()

    run = Path(args.run_dir) if args.run_dir else find_latest(Path(args.root))
    print(f"[export] run = {run}")

    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    acc = EventAccumulator(str(run), size_guidance={"scalars": 0})
    acc.Reload()
    have = set(acc.Tags().get("scalars", []))
    print(f"[export] {len(have)} scalar tags")

    series: dict[str, list] = {}
    iters: list[int] = []
    for key, tag in TAGS.items():
        if tag not in have:
            continue
        events = acc.Scalars(tag)
        series[key] = [round(float(e.value), 5) for e in events]
        if not iters:
            iters = [int(e.step) for e in events]

    payload = {
        "run": run.name,
        "iter_count": len(iters),
        "iters": iters,
        "series": series,
        "tags_missing": [t for t in TAGS.values() if t not in have],
    }
    out = Path(args.out)
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"[export] wrote {out} ({out.stat().st_size} bytes, {len(iters)} pts)")
    for k, v in series.items():
        if v:
            print(f"  {k:20s} first={v[0]:>9.4f}  last={v[-1]:>9.4f}  min={min(v):>9.4f}  max={max(v):>9.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
