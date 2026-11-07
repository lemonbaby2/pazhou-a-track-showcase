"""仿真入口。

用法（在工程根目录）::

    python -m sim.run_sim
    python -m sim.run_sim --seed 3 --out out/seed3
    python -m sim.run_sim --no-gif

产物：
    out/run.jsonl        结构化事件日志
    out/demo.gif         任务全程俯视演示
    out/keyframes.png    4 个关键帧拼图
    out/timeline.png     状态时间线
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict

import yaml

# 允许直接 `python sim/run_sim.py` 也能跑
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from bev.interfaces import RobotIO
from bev.logger import EventLogger
from bev.mock_world import MockWorld
from bev.perception import MockVision
from bev.task import BeverageTask
from bev.tray import TrayMonitor
from bev.voice import build_voice
from sim.render import save_gif, save_keyframes, save_timeline


def load_cfg(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="A 赛道饮品服务任务仿真")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "task.yaml"))
    ap.add_argument("--out", default=os.path.join(ROOT, "out"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--no-gif", action="store_true")
    args = ap.parse_args(argv)

    cfg = load_cfg(args.config)
    os.makedirs(args.out, exist_ok=True)

    log = EventLogger(os.path.join(args.out, "run.jsonl"))
    tray = TrayMonitor(cfg["tray"]["tilt_limit_deg"], cfg["tray"]["tilt_warn_deg"])
    world = MockWorld(cfg, logger=log, tray=tray, seed=args.seed)
    voice = build_voice(cfg["voice"]["backend"], log)

    io = RobotIO(
        nav=world,
        arm=world,
        gripper=world,
        vision=MockVision(world),
        voice=voice,
        clock=None,  # 仿真不需要真实时钟
    )

    log.log("BOOT", "config", msg="配置载入", seed=world.seed,
            time_limit_s=cfg["task"]["time_limit_s"])

    task = BeverageTask(io, cfg, log, tray, world)
    stats = task.run()

    success = world.table_count() == 2
    print("\n================ 结果汇总 ================")
    print("任务状态      :", task.state.value)
    print("桌面饮品数    : %d / 2" % world.table_count())
    print("托盘剩余      : %d" % world.tray_count())
    print("仿真用时      : %.1f s（规定上限 %d s）" % (world.time_s, cfg["task"]["time_limit_s"]))
    print("最大托盘倾角  : %.1f°（上限 %.1f°）" % (stats["max_tilt_deg"], cfg["tray"]["tilt_limit_deg"]))
    print("导航重试      : %d" % stats["nav_retries"])
    print("抓取尝试/失败 : %d / %d" % (stats["grasp_attempts"], stats["grasp_failures"]))
    print("放置重试      : %d" % stats["place_retries"])
    print("倾角恢复      : %d" % stats["tilt_recoveries"])
    print("成功          :", "✅ YES" if success else "❌ NO")
    print("==========================================")

    if not args.no_gif:
        gif = save_gif(world.frames, cfg, os.path.join(args.out, "demo.gif"),
                       fps=int(cfg["sim"].get("render_fps", 12)))
        kf = save_keyframes(world.frames, cfg, os.path.join(args.out, "keyframes.png"))
        tl = save_timeline(world.frames, os.path.join(args.out, "timeline.png"))
        print("演示 GIF      :", gif)
        print("关键帧        :", kf)
        print("时间线        :", tl)

    print("事件日志      :", os.path.join(args.out, "run.jsonl"))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
