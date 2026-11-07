"""A 赛道任务状态机。

流程严格对齐赛题：
  启动服务 → 备餐装盘（2 瓶）→ 端盘配送 → 逐份上饮 + 语音通知

异常恢复：
  - 导航失败：重试 + 回 home 重新定位
  - 抓取失败：重试 + 重新检测
  - 放置未释放：重复开爪
  - 托盘倾角超限：调平后重走该段
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from .interfaces import RobotIO
from .tray import TrayMonitor


class State(str, Enum):
    BOOT = "BOOT"
    ANNOUNCE = "ANNOUNCE"
    NAV_PREP = "NAV_PREP"
    DETECT = "DETECT"
    PICK_PLACE_1 = "PICK_PLACE_1"
    PICK_PLACE_2 = "PICK_PLACE_2"
    NAV_GUEST = "NAV_GUEST"
    SERVE_1 = "SERVE_1"
    SERVE_2 = "SERVE_2"
    DONE = "DONE"
    ABORT = "ABORT"


class TaskAborted(Exception):
    pass


class BeverageTask:
    def __init__(self, io: RobotIO, cfg: dict, log, tray: TrayMonitor, world=None):
        self.io = io
        self.cfg = cfg
        self.log = log
        self.tray = tray
        self.world = world

        rec = cfg.get("recovery", {})
        self.nav_max = int(rec.get("nav_max_retry", 2))
        self.pick_max = int(rec.get("pick_max_retry", 3))
        self.step_timeout = float(rec.get("step_timeout_s", 45))

        self.tray_limit = float(cfg["tray"]["tilt_limit_deg"])
        self.tray_warn = float(cfg["tray"]["tilt_warn_deg"])
        self.time_limit = float(cfg.get("task", {}).get("time_limit_s", 300))

        self.state = State.BOOT
        self.stats = {
            "nav_retries": 0,
            "grasp_attempts": 0,
            "grasp_failures": 0,
            "place_retries": 0,
            "tilt_recoveries": 0,
            "served": 0,
            "max_tilt_deg": 0.0,
        }

    # ---------- 基础 ----------
    def _set(self, state: State) -> None:
        self.state = state
        if self.world is not None:
            self.world.current_state = state.value
        self.log.log(state.value, "enter", msg="进入 %s" % state.value)
        if self.world is not None:
            self.world.snapshot()

    def _check_time(self) -> None:
        if self.world is None:
            return
        if self.world.time_s > self.time_limit:
            raise TaskAborted("超出单轮规定用时 %.0fs" % self.time_limit)

    def _check_tray(self) -> bool:
        tilt = self.tray.peak_deg
        self.stats["max_tilt_deg"] = max(self.stats["max_tilt_deg"], tilt)
        if self.tray.exceeded:
            self.stats["tilt_recoveries"] += 1
            self.log.log(self.state.value, "tilt_exceeded",
                         msg="托盘倾角 %.1f° 超限，调平恢复" % tilt)
            self.io.arm.move_to("level_tray", 10)
            self.io.arm.move_to("home", 10)
            self.tray.reset()
            return False
        if self.tray.warning:
            self.log.log(self.state.value, "tilt_warn",
                         msg="托盘倾角 %.1f° 接近阈值" % tilt)
        return True

    # ---------- 导航 ----------
    def _nav(self, waypoint: str) -> None:
        attempts = self.nav_max + 1
        for i in range(1, attempts + 1):
            self._check_time()
            ok = self.io.nav.goto(waypoint, self.step_timeout)
            if ok:
                if not self._check_tray():
                    self.log.log(self.state.value, "tilt_recovered",
                                 msg="调平完成，继续任务")
                self.log.log(self.state.value, "nav_ok", msg="到达 %s" % waypoint)
                return
            self.stats["nav_retries"] += 1
            self.log.log(self.state.value, "nav_retry",
                         msg="第 %d/%d 次导航 %s 失败，重新定位" % (i, attempts, waypoint))
            self.io.arm.move_to("home", 8)
        raise TaskAborted("导航到 %s 连续失败" % waypoint)

    # ---------- 备餐装盘 ----------
    def _detect(self) -> int:
        dets = self.io.vision.detect(["bottle"])
        self.log.log(self.state.value, "detect", msg="检测到 %d 瓶饮品" % len(dets))
        return len(dets)

    def _pick_and_place(self, idx: int) -> None:
        self._set(State.PICK_PLACE_1 if idx == 1 else State.PICK_PLACE_2)
        for attempt in range(1, self.pick_max + 1):
            self._check_time()
            self.stats["grasp_attempts"] += 1
            self.io.arm.move_to("prep_bottle", 10)
            if not self.io.gripper.close():
                self.stats["grasp_failures"] += 1
                self.log.log(self.state.value, "grasp_fail",
                             msg="第 %d/%d 次抓取第 %d 瓶失败" % (attempt, self.pick_max, idx))
                self.io.gripper.open()
                self.io.arm.move_to("home", 5)
                self._detect()
                continue

            self.log.log(self.state.value, "grasp_ok", msg="已夹住第 %d 瓶" % idx)
            self.io.arm.move_to("lift", 6)
            self.io.arm.move_to("tray", 10)
            if self._try_release("tray"):
                self.log.log(self.state.value, "place_ok", msg="第 %d 瓶已放入托盘" % idx)
                self.io.arm.move_to("home", 6)
                return
            self.io.arm.move_to("home", 6)

        raise TaskAborted("第 %d 瓶抓取/装盘失败（已重试 %d 次）" % (idx, self.pick_max))

    def _try_release(self, target: str = "tray") -> bool:
        for k in range(1, 4):
            self.io.gripper.open()
            if not self.io.gripper.is_holding():
                return True
            self.stats["place_retries"] += 1
            self.log.log(self.state.value, "place_retry",
                         msg="第 %d 次未释放，重新对准 %s" % (k, target))
            self.io.arm.move_to(target, 6)
        return False

    # ---------- 上饮 ----------
    def _serve(self, idx: int) -> None:
        self._set(State.SERVE_1 if idx == 1 else State.SERVE_2)
        for attempt in range(1, 4):
            self._check_time()
            self.io.arm.move_to("tray", 8)
            if not self.io.gripper.close():
                self.log.log(self.state.value, "serve_grasp_fail",
                             msg="第 %d 次取第 %d 瓶失败" % (attempt, idx))
                self.io.arm.move_to("home", 5)
                continue
            self.io.arm.move_to("lift", 5)
            self.io.arm.move_to("guest_table", 10)
            if not self._try_release("guest_table"):
                self.log.log(self.state.value, "serve_place_retry",
                             msg="第 %d 瓶未放稳，重试" % idx)
                self.io.arm.move_to("home", 5)
                continue
            self.io.arm.move_to("home", 6)
            self.stats["served"] += 1
            self.io.voice.say("这是您的第 %d 瓶水，请慢用。" % idx)
            self.log.log(self.state.value, "served", msg="第 %d 瓶已上桌" % idx)
            return
        raise TaskAborted("第 %d 瓶上桌失败" % idx)

    # ---------- 主流程 ----------
    def run(self) -> dict:
        self._set(State.BOOT)
        self.log.log("BOOT", "selfcheck",
                     msg="自检：托盘已夹稳，2 瓶饮品就位",
                     tray_limit_deg=self.tray_limit, step_timeout_s=self.step_timeout)

        self._set(State.ANNOUNCE)
        self.io.voice.say("您好，开始为您服务，请稍候。")
        self.log.log("ANNOUNCE", "announce", msg="已播报开始服务")

        try:
            self._set(State.NAV_PREP)
            self._nav("prep")

            self._set(State.DETECT)
            n = self._detect()
            if n < 2:
                raise TaskAborted("检测到的饮品不足 2 瓶（实际 %d）" % n)

            self._pick_and_place(1)
            self._pick_and_place(2)

            self._set(State.NAV_GUEST)
            self._nav("guest")

            self._serve(1)
            self._serve(2)

            self._set(State.DONE)
            self.io.voice.say("您的饮品已全部送达，祝您用餐愉快。")
            self.log.log("DONE", "done", msg="任务完成", **{k: v for k, v in self.stats.items()})
        except TaskAborted as e:
            self._set(State.ABORT)
            self.log.log("ABORT", "abort", msg=str(e), **{k: v for k, v in self.stats.items()})
            self.io.voice.say("服务出现异常，请联系工作人员。")

        return self.stats
