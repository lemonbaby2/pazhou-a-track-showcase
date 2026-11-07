"""平台无关的机器人能力接口。

比赛方提供「基础导航、机械臂、夹爪、视觉、语音」接口，但接口形态未知。
本文件把它们抽象成最小 Protocol，任务层只依赖这里；
官方 SDK 公布后，只需在 ``bev/adapters/vendor_sdk.py`` 里实现这几个方法。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Tuple


@dataclass
class Pose:
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0  # 弧度


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2（像素）
    center: Tuple[float, float]              # 像素中心
    depth_m: Optional[float] = None          # 可选：深度（米）


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class Navigation(Protocol):
    """轮式底盘导航。goto 返回 True 表示到达。"""

    def goto(self, waypoint: str, timeout_s: float) -> bool: ...

    def pose(self) -> Pose: ...


class Arm(Protocol):
    """机械臂位姿调用。move_to 返回 True 表示到位。"""

    def move_to(self, target: str, timeout_s: float) -> bool: ...


class Gripper(Protocol):
    """双指夹爪。close 返回 True 表示夹到物体。"""

    def open(self) -> None: ...

    def close(self) -> bool: ...

    def is_holding(self) -> bool: ...


class Vision(Protocol):
    def detect(self, labels: List[str]) -> List[Detection]: ...


class Voice(Protocol):
    def say(self, text: str) -> None: ...


@dataclass
class RobotIO:
    """把五类能力打包，便于任务层注入与测试替身。"""

    nav: Navigation
    arm: Arm
    gripper: Gripper
    vision: Vision
    voice: Voice
    clock: Clock
    tray_tilt_deg: float = 0.0
    extra: dict = field(default_factory=dict)
