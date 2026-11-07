"""二维仿真世界：在没有比赛机器人时，完整复现 A 赛道任务。

它同时实现 Navigation / Arm / Gripper 三个协议，并把每次状态快照记录下来，
供 ``sim/render.py`` 渲染成演示动图。随机失败（导航、抓取、释放、托盘倾斜）
由配置控制，用来验证异常恢复逻辑。
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional

from .interfaces import Pose


class MockWorld:
    def __init__(self, cfg: dict, logger=None, tray=None, seed: Optional[int] = None):
        self.cfg = cfg
        self.log = logger
        self.tray = tray
        sim = cfg.get("sim", {})
        seed_val = seed if seed is not None else sim.get("seed", 7)
        self.seed = int(seed_val)
        self.rng = random.Random(self.seed)
        self.nav_fail_prob = float(sim.get("nav_fail_prob", 0.05))
        self.pick_fail_prob = float(sim.get("pick_fail_prob", 0.12))
        self.place_fail_prob = float(sim.get("place_fail_prob", 0.08))
        self.tilt_noise = float(sim.get("tilt_noise_deg", 1.5))
        self.tilt_spike_prob = float(sim.get("tilt_spike_prob", 0.35))

        layout = cfg["layout"]
        self.waypoints = {
            "standby": layout["standby"],
            "prep": layout["prep"],
            "guest": layout["guest"],
        }
        self.guest_table = tuple(layout["guest_table"])

        self.pose = Pose(float(layout["standby"]["x"]), float(layout["standby"]["y"]),
                         float(layout["standby"].get("yaw", 0.0)))
        self.location = "standby"
        self.bottles: List[Dict] = [
            {"id": "D1", "pos": tuple(layout["prep_bottles"][0]), "loc": "prep"},
            {"id": "D2", "pos": tuple(layout["prep_bottles"][1]), "loc": "prep"},
        ]
        self.holding: Optional[str] = None
        self.arm_target = "home"
        self.time_s = 0.0
        self.current_state = "BOOT"
        self.frames: List[Dict] = []
        self._spike_step = -1

    # ---------- 状态查询 ----------
    def tray_count(self) -> int:
        return sum(1 for b in self.bottles if b["loc"] == "tray")

    def table_count(self) -> int:
        return sum(1 for b in self.bottles if b["loc"] == "table")

    def pose(self) -> Pose:
        return Pose(self.pose.x, self.pose.y, self.pose.yaw)

    def is_holding(self) -> bool:
        return self.holding is not None

    # ---------- 内部 ----------
    def _tick(self, dt: float) -> None:
        self.time_s += max(0.0, dt)

    def _update_tilt(self, nav_step: int = -1) -> None:
        if self.tray is None:
            return
        carrying = self.tray_count() > 0
        if not carrying:
            self.tray.update(self.rng.gauss(0, 0.25))
            return
        tilt = self.rng.gauss(0, self.tilt_noise)
        if nav_step >= 0 and nav_step == self._spike_step:
            tilt += self.rng.choice([-1, 1]) * self.rng.uniform(8.6, 12.5)
        self.tray.update(tilt)

    def snapshot(self) -> None:
        self.frames.append(
            {
                "t": self.time_s,
                "state": self.current_state,
                "x": self.pose.x,
                "y": self.pose.y,
                "yaw": self.pose.yaw,
                "location": self.location,
                "holding": self.holding,
                "tilt": round(self.tray.tilt_deg, 2) if self.tray else 0.0,
                "bottles": [(b["id"], b["pos"][0], b["pos"][1], b["loc"]) for b in self.bottles],
                "tray_count": self.tray_count(),
                "table_count": self.table_count(),
            }
        )

    # ---------- Navigation ----------
    def goto(self, waypoint: str, timeout_s: float) -> bool:
        if waypoint not in self.waypoints:
            if self.log:
                self.log.log(self.current_state, "nav_bad_target", msg=waypoint)
            return False
        if self.rng.random() < self.nav_fail_prob:
            if self.log:
                self.log.log(self.current_state, "nav_fail", msg="导航到 %s 失败（定位丢失）" % waypoint)
            self._tick(1.0)
            return False

        target = self.waypoints[waypoint]
        x0, y0, yaw0 = self.pose.x, self.pose.y, self.pose.yaw
        x1, y1 = float(target["x"]), float(target["y"])
        yaw1 = float(target.get("yaw", yaw0))
        steps = 20
        dt = max(0.05, min(0.25, float(timeout_s) / max(1, steps)))

        self._spike_step = -1
        if self.tray_count() > 0 and self.rng.random() < self.tilt_spike_prob:
            self._spike_step = self.rng.randint(steps // 3, (2 * steps) // 3)

        self.location = "transit"
        for i in range(1, steps + 1):
            k = i / steps
            self.pose.x = x0 + (x1 - x0) * k
            self.pose.y = y0 + (y1 - y0) * k
            self.pose.yaw = yaw0 + (yaw1 - yaw0) * k
            self._update_tilt(nav_step=i)
            self._tick(dt)
            self.snapshot()
        self.location = waypoint
        self._spike_step = -1
        return True

    # ---------- Arm ----------
    def move_to(self, target: str, timeout_s: float) -> bool:
        self.arm_target = target
        self._tick(0.6)
        self.snapshot()
        return True

    # ---------- Gripper ----------
    def open(self) -> None:
        if not self.holding:
            return
        if self.rng.random() < self.place_fail_prob:
            if self.log:
                self.log.log(self.current_state, "release_fail", msg="夹爪未完全张开，物体仍被夹持")
            self._tick(0.3)
            self.snapshot()
            return
        bid = self.holding
        b = next(x for x in self.bottles if x["id"] == bid)
        if self.arm_target == "tray":
            b["loc"] = "tray"
            b["pos"] = (self.pose.x + 0.12, self.pose.y + 0.10)
        elif self.arm_target == "guest_table":
            b["loc"] = "table"
            b["pos"] = self.guest_table
        else:
            b["loc"] = "prep"
        self.holding = None
        self._tick(0.4)
        self.snapshot()

    def close(self) -> bool:
        if self.holding:
            return True
        cand = [b for b in self.bottles if b["loc"] == "prep"]
        if not cand and self.arm_target in ("tray", "guest_bottle"):
            cand = [b for b in self.bottles if b["loc"] == "tray"]
        if not cand:
            if self.log:
                self.log.log(self.current_state, "grasp_none", msg="备餐台/托盘无可抓取饮品")
            return False
        if self.rng.random() < self.pick_fail_prob:
            if self.log:
                self.log.log(self.current_state, "grasp_fail", msg="夹爪闭合未夹住饮品")
            self._tick(0.4)
            self.snapshot()
            return False
        b = cand[0]
        b["loc"] = "held"
        self.holding = b["id"]
        self._tick(0.5)
        self.snapshot()
        return True
