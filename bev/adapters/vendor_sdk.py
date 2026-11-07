"""官方 SDK 适配层（占位模板）。

比赛方提供「基础导航、机械臂、夹爪、视觉、语音」接口，接口说明与示例统一公布。
公布后，只需在这里把官方对象包成 ``bev.interfaces`` 的 5 个方法，
**任务层（bev/task.py）与仿真层完全不用改**。

接入步骤：
1. 用官方 SDK 建立连接；
2. 按下面 5 个类填 TODO；
3. ``io = build_robot_io(sdk)``，交给 ``BeverageTask`` 即可。

现场标定注意：
- waypoint 名（standby / prep / guest）需与场地实际标定点一一对应；
- 夹爪 ``close()`` 的返回值要用真实反馈（电流/位置/力）判断是否夹到；
- 语音优先本地离线 TTS，禁止云端。
"""

from __future__ import annotations

from typing import List

from ..interfaces import Detection, Pose


class VendorNav:
    def __init__(self, sdk):
        self.sdk = sdk

    def goto(self, waypoint: str, timeout_s: float) -> bool:
        # TODO: 换成官方导航，例如：
        #   return self.sdk.navigation.goto_named(waypoint, timeout=timeout_s)
        raise NotImplementedError("接入官方导航接口：goto(%r)" % waypoint)

    def pose(self) -> Pose:
        # TODO: p = self.sdk.navigation.get_pose()
        #       return Pose(p.x, p.y, p.yaw)
        raise NotImplementedError("接入官方定位接口：pose()")


class VendorArm:
    def __init__(self, sdk):
        self.sdk = sdk

    def move_to(self, target: str, timeout_s: float) -> bool:
        # TODO: 官方机械臂位姿调用，target 可为命名位姿或关节角
        raise NotImplementedError("接入官方机械臂接口：move_to(%r)" % target)


class VendorGripper:
    def __init__(self, sdk):
        self.sdk = sdk

    def open(self) -> None:
        # TODO: self.sdk.gripper.open()
        raise NotImplementedError("接入官方夹爪接口：open()")

    def close(self) -> bool:
        # TODO: ok = self.sdk.gripper.close()
        #       用真实反馈判断是否夹到（电流阈值/位置到达/力传感器）
        raise NotImplementedError("接入官方夹爪接口：close()")

    def is_holding(self) -> bool:
        raise NotImplementedError("接入官方夹爪接口：is_holding()")


class VendorVision:
    def __init__(self, sdk):
        self.sdk = sdk

    def detect(self, labels: List[str]) -> List[Detection]:
        # TODO: frame = self.sdk.camera.read()
        #       参考 bev/perception.py 的 YoloVision
        raise NotImplementedError("接入官方视觉接口：detect(%r)" % (labels,))


class VendorVoice:
    def __init__(self, sdk):
        self.sdk = sdk

    def say(self, text: str) -> None:
        # TODO: 官方语音接口；或退回 bev.voice.SapiVoice（Windows 离线）
        raise NotImplementedError("接入官方语音接口：say(%r)" % text)


def build_robot_io(sdk):
    """一行接入：把官方 SDK 包成 RobotIO。"""
    from ..interfaces import RobotIO

    return RobotIO(
        nav=VendorNav(sdk),
        arm=VendorArm(sdk),
        gripper=VendorGripper(sdk),
        vision=VendorVision(sdk),
        voice=VendorVoice(sdk),
        clock=None,
    )
