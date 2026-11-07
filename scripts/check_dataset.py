"""数据集质检 CLI：把"采完才发现数据废了"提前到"采完立刻知道"。

用法::

    python -m scripts.check_dataset --root data/raw
    python -m scripts.check_dataset --root data/raw --joint-limit 3.2 --min-episodes 50
    python -m scripts.check_dataset --root data/raw --fail-on warn   # CI 里严一点

退出码：0 = 通过；1 = 有 error（或 --fail-on warn 时有 warn）；2 = 参数/数据缺失。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bev.dataset import QCConfig, iter_episodes, validate_dataset, write_report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="示教数据集质检")
    ap.add_argument("--root", default="data/raw", help="数据集根目录")
    ap.add_argument("--report", default="out/qc_report.json")
    ap.add_argument("--fps", type=float, default=None, help="不填则按时间戳自动推断")
    ap.add_argument("--min-episodes", type=int, default=20)
    ap.add_argument("--min-duration", type=float, default=1.0)
    ap.add_argument("--max-duration", type=float, default=30.0)
    ap.add_argument("--joint-limit", type=float, default=None,
                    help="真机数据建议 3.2（rad）；仿真/抽象动作空间不要给")
    ap.add_argument("--gripper-range", default="0,1", help="夹爪维度范围，'off' 关闭")
    ap.add_argument("--fail-on", choices=["error", "warn"], default="error")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print("数据集目录不存在：%s" % root, file=sys.stderr)
        return 2
    if not any(iter_episodes(root)):
        print("目录下没有 episode：%s" % root, file=sys.stderr)
        return 2

    gr = None
    if args.gripper_range.lower() != "off":
        lo, hi = (float(x) for x in args.gripper_range.split(","))
        gr = (lo, hi)

    cfg = QCConfig(
        fps=args.fps,
        min_duration_s=args.min_duration,
        max_duration_s=args.max_duration,
        joint_limit_rad=args.joint_limit,
        gripper_range=gr,
        min_episodes=args.min_episodes,
    )
    rep = validate_dataset(root, cfg)
    p = write_report(rep, args.report)
    print("报告 → %s" % p)

    ok = rep["ok"] if args.fail_on == "error" else (rep["errors"] == 0 and rep["warns"] == 0)
    print("判定：%s" % ("通过" if ok else "不通过"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
