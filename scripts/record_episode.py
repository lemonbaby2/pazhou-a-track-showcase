"""采集（或回放）示教轨迹，落成 bev.dataset 标准格式。

真机接管时只改一处：把 ``_frames_from_sim`` 换成从你的 SDK 读
``(关节角, 夹爪, 时间戳)``。其余（分段、指令、写盘、质检）完全复用。

用法::

    # 用仿真跑 3 条任务，按技能段切成 episode 落盘（备赛期演练完整流程）
    python -m scripts.record_episode --out data/raw --episodes 3

    # 把已有的一次运行日志转成数据集（复盘旧数据）
    python -m scripts.record_episode --source jsonl --jsonl out/run.jsonl --out data/raw
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from bev.dataset import EpisodeRecorder, validate_dataset, write_report
from bev.interfaces import RobotIO
from bev.logger import EventLogger
from bev.mock_world import MockWorld
from bev.perception import MockVision
from bev.task import BeverageTask
from bev.tray import TrayMonitor
from bev.voice import MockVoice

# 状态 → 语言指令。VLA 训练时这条指令就是 task 文本，语义必须固定、不复用。
INSTRUCTIONS: Dict[str, str] = {
    "BOOT": "上电待机",
    "ANNOUNCE": "语音播报开始服务",
    "NAV_PREP": "从待命位移动到备餐台",
    "DETECT": "在备餐台识别饮品瓶",
    "PICK_PLACE_1": "抓取第 1 瓶饮品并放入托盘",
    "PICK_PLACE_2": "抓取第 2 瓶饮品并放入托盘",
    "NAV_GUEST": "端着托盘移动到客人桌位",
    "SERVE_1": "把第 1 瓶饮品放到客人桌面",
    "SERVE_2": "把第 2 瓶饮品放到客人桌面",
    "DONE": "任务完成返回待命",
    "ABORT": "异常中止",
}

ARM_IDX = {"home": 0, "prep_bottle": 1, "prep_bottle_2": 1, "tray": 2,
           "guest_bottle": 3, "guest_table": 4, "level_tray": 5}


def _f(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _frames_from_sim(cfg: Dict[str, Any], seed: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """跑一次仿真任务，返回逐帧快照与结果统计。"""
    tray = TrayMonitor(cfg["tray"]["tilt_limit_deg"], cfg["tray"]["tilt_warn_deg"])
    log = EventLogger(path=None, echo=False)
    world = MockWorld(cfg, logger=log, tray=tray, seed=seed)
    io = RobotIO(
        nav=world, arm=world, gripper=world,
        vision=MockVision(world), voice=MockVoice(log), clock=None,
    )
    task = BeverageTask(io, cfg, log, tray, world)
    stats = task.run()
    return world.frames, {"stats": stats, "state": task.state.name, "seed": seed}


def _frames_from_jsonl(path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """从 run.jsonl 事件日志重建"帧"（粒度是事件，不是控制周期，仅用于复盘）。"""
    frames: List[Dict[str, Any]] = []
    t = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = _f(rec.get("t"), t)
        frames.append({
            "t": t,
            "state": rec.get("step", "UNKNOWN"),
            "x": 0.0, "y": 0.0, "yaw": 0.0,
            "tilt": 0.0, "holding": None,
        })
    return frames, {"stats": {}, "state": "UNKNOWN", "seed": -1}


def _to_vec(f: Dict[str, Any]) -> List[float]:
    return [
        _f(f.get("x")), _f(f.get("y")), _f(f.get("yaw")),
        _f(f.get("tilt")), 1.0 if f.get("holding") else 0.0,
    ]


def _segment(frames: List[Dict[str, Any]], min_frames: int) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """按状态字段切成连续段——一段 = 一个完整子技能，这是采集的第一原则。"""
    out: List[Tuple[str, List[Dict[str, Any]]]] = []
    cur: Optional[str] = None
    buf: List[Dict[str, Any]] = []
    for f in frames:
        st = str(f.get("state", "UNKNOWN"))
        if st != cur:
            if cur is not None and len(buf) >= min_frames:
                out.append((cur, buf))
            cur, buf = st, [f]
        else:
            buf.append(f)
    if cur is not None and len(buf) >= min_frames:
        out.append((cur, buf))
    return out


def record(
    out: str | Path,
    cfg: Dict[str, Any],
    episodes: int = 1,
    seed: int = 1,
    fps: float = 30.0,
    min_frames: int = 8,
    source: str = "sim",
    jsonl: Optional[str] = None,
    operator: str = "",
) -> int:
    rec = EpisodeRecorder(
        root=out,
        task=cfg.get("_task_name", "beverage_service"),
        fps=fps,
        cameras=("front",),
        operator=operator,
        extra_meta={"source": source, "config": "config/task.yaml"},
    )
    n = 0
    for k in range(episodes):
        s = seed + k
        if source == "jsonl":
            frames, info = _frames_from_jsonl(Path(jsonl))  # type: ignore[arg-type]
        else:
            frames, info = _frames_from_sim(cfg, s)
        segs = _segment(frames, min_frames)
        for name, buf in segs:
            rec.start_episode(
                instruction=INSTRUCTIONS.get(name, name),
                labels={
                    "skill": name,
                    "seed": s,
                    "source": source,
                    "lighting": "sim",
                    "bottle_offset_cm": 0,
                },
            )
            t0 = _f(buf[0].get("t"), 0.0)
            for f in buf:
                # 用源时间戳，不假装等间隔：采样率由数据决定，质检会自动推断
                rec.add_frame(_to_vec(f), t=_f(f.get("t"), 0.0) - t0)
            rec.end_episode(success=(info["state"] == "DONE"), note=info["state"])
            n += 1
        print("seed=%s 段数=%d 任务态=%s" % (s, len(segs), info["state"]))
    return n


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="示教轨迹采集 / 回放")
    ap.add_argument("--config", default="config/task.yaml")
    ap.add_argument("--out", default="data/raw", help="数据集根目录（应加入 .gitignore）")
    ap.add_argument("--episodes", type=int, default=1, help="跑几次任务（每次一个 seed）")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--min-frames", type=int, default=8, help="短于此帧数的段丢弃")
    ap.add_argument("--source", choices=["sim", "jsonl"], default="sim")
    ap.add_argument("--jsonl", default=None)
    ap.add_argument("--operator", default="")
    ap.add_argument("--qc", action="store_true", help="采完立刻质检")
    ap.add_argument("--report", default="out/qc_report.json")
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    cfg["_task_name"] = "beverage_service"

    if args.source == "jsonl" and not args.jsonl:
        print("--source jsonl 需要同时给 --jsonl", file=sys.stderr)
        return 2

    n = record(args.out, cfg, args.episodes, args.seed, args.fps,
               args.min_frames, args.source, args.jsonl, args.operator)
    print("已写入 %d 条 episode → %s" % (n, args.out))

    if args.qc:
        print("\n=== 质检 ===")
        rep = validate_dataset(args.out)
        write_report(rep, args.report)
        print("报告 → %s" % args.report)
        return 0 if rep["ok"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
