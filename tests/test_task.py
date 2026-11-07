"""状态机与异常恢复单元测试（不依赖仿真世界，用替身精确注入故障）。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

from bev.interfaces import Detection, RobotIO
from bev.logger import EventLogger
from bev.task import BeverageTask, State
from bev.tray import TrayMonitor

CFG = {
    "task": {"time_limit_s": 300, "total_budget_s": 5400},
    "layout": {
        "standby": {"x": 0, "y": 0, "yaw": 0},
        "prep": {"x": 2, "y": 0, "yaw": 0},
        "guest": {"x": 4, "y": 2, "yaw": 1.57},
        "prep_bottles": [[2.2, -0.2], [2.2, 0.2]],
        "guest_table": [4.5, 2.0],
    },
    "tray": {"tilt_limit_deg": 8.0, "tilt_warn_deg": 5.0},
    "recovery": {"nav_max_retry": 2, "pick_max_retry": 3, "place_max_retry": 2,
                 "step_timeout_s": 45},
}


class FakeNav:
    def __init__(self, fail_times=0, tray=None, tilt_on_guest=None):
        self.fail_times = fail_times
        self.calls = []
        self.tray = tray
        self.tilt_on_guest = tilt_on_guest

    def goto(self, waypoint, timeout_s):
        self.calls.append(waypoint)
        if self.fail_times > 0:
            self.fail_times -= 1
            return False
        if waypoint == "guest" and self.tilt_on_guest is not None and self.tray:
            self.tray.update(self.tilt_on_guest)
        return True

    def pose(self):
        return None


class FakeArm:
    def __init__(self):
        self.targets = []

    def move_to(self, target, timeout_s):
        self.targets.append(target)
        return True


class FakeGripper:
    def __init__(self, fail_closes=0, fail_opens=0):
        self.fail_closes = fail_closes
        self.fail_opens = fail_opens
        self.holding = False

    def open(self):
        if self.fail_opens > 0:
            self.fail_opens -= 1
            return
        self.holding = False

    def close(self):
        if self.fail_closes > 0:
            self.fail_closes -= 1
            self.holding = False
            return False
        self.holding = True
        return True

    def is_holding(self):
        return self.holding


class FakeVision:
    def detect(self, labels):
        return [Detection("bottle", 0.9, (0, 0, 10, 40), (5, 20), 1.2) for _ in range(2)]


class FakeVoice:
    def __init__(self):
        self.said = []

    def say(self, text):
        self.said.append(text)


def build(nav=None, gripper=None, tray=None):
    tray = tray or TrayMonitor(8.0, 5.0)
    nav = nav or FakeNav(tray=tray)
    arm = FakeArm()
    gripper = gripper or FakeGripper()
    voice = FakeVoice()
    io = RobotIO(nav=nav, arm=arm, gripper=gripper,
                 vision=FakeVision(), voice=voice, clock=None)
    log = EventLogger(path=None, echo=False)
    task = BeverageTask(io, CFG, log, tray, world=None)
    return task, nav, gripper, voice, tray


def test_happy_path_completes():
    task, nav, gripper, voice, tray = build()
    stats = task.run()
    assert task.state == State.DONE
    assert stats["served"] == 2
    assert stats["grasp_failures"] == 0
    assert "prep" in nav.calls and "guest" in nav.calls
    assert any("第 1 瓶水" in s for s in voice.said)


def test_grasp_failure_recovers():
    gripper = FakeGripper(fail_closes=2)
    task, nav, gripper, voice, tray = build(gripper=gripper)
    stats = task.run()
    assert task.state == State.DONE
    assert stats["grasp_failures"] == 2
    assert stats["served"] == 2


def test_nav_failure_recovers():
    tray = TrayMonitor(8.0, 5.0)
    nav = FakeNav(fail_times=2, tray=tray)
    task, nav, gripper, voice, tray = build(nav=nav, tray=tray)
    stats = task.run()
    assert task.state == State.DONE
    assert stats["nav_retries"] == 2


def test_nav_abort_after_retries():
    tray = TrayMonitor(8.0, 5.0)
    nav = FakeNav(fail_times=99, tray=tray)
    task, nav, gripper, voice, tray = build(nav=nav, tray=tray)
    task.run()
    assert task.state == State.ABORT


def test_tilt_recovery():
    tray = TrayMonitor(8.0, 5.0)
    nav = FakeNav(tray=tray, tilt_on_guest=12.5)
    task, nav, gripper, voice, tray = build(nav=nav, tray=tray)
    stats = task.run()
    assert task.state == State.DONE
    assert stats["tilt_recoveries"] >= 1
    assert task.stats["max_tilt_deg"] >= 12.0


def test_place_release_retry():
    gripper = FakeGripper(fail_opens=1)
    task, nav, gripper, voice, tray = build(gripper=gripper)
    stats = task.run()
    assert task.state == State.DONE
    assert stats["place_retries"] >= 1
    assert stats["served"] == 2
