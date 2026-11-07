"""感知层：瓶装水 / 托盘 / 桌面检测。

- MockVision：由仿真世界直接给出真值，保证无相机也能跑通全流程；
- YoloVision：预留接口，官方 SDK 或自训练 YOLO 模型公布后接上即可。
"""

from __future__ import annotations

from typing import List, Optional

from .interfaces import Detection


class MockVision:
    """从仿真世界读取真值，产出与真实检测同构的结果。"""

    def __init__(self, world):
        self.world = world

    def detect(self, labels: List[str]) -> List[Detection]:
        out: List[Detection] = []
        want_bottle = "bottle" in labels or "water" in labels
        if want_bottle:
            for i, b in enumerate(self.world.bottles):
                if b["loc"] in ("prep", "tray", "table"):
                    x, y = b["pos"]
                    cx, cy = 320 + x * 80, 240 - y * 80
                    out.append(
                        Detection(
                            label="bottle",
                            confidence=0.92,
                            bbox=(cx - 14, cy - 40, cx + 14, cy + 40),
                            center=(cx, cy),
                            depth_m=1.2,
                        )
                    )
        return out


class YoloVision:
    """真实相机 + YOLO 的接入点。

    用法（官方 SDK 提供取图接口后）::

        v = YoloVision(frame_getter=my_camera.read, weights="bottle.pt")
        dets = v.detect(["bottle"])
    """

    def __init__(self, frame_getter, weights: str = "bottle.pt", conf: float = 0.35):
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "未安装 ultralytics，无法启用 YoloVision；比赛前请预装离线 wheel。"
            ) from e
        self.model = YOLO(weights)
        self.frame_getter = frame_getter
        self.conf = conf

    def detect(self, labels: List[str]) -> List[Detection]:  # pragma: no cover
        frame = self.frame_getter()
        res = self.model.predict(frame, conf=self.conf, verbose=False)[0]
        out: List[Detection] = []
        names = res.names
        for box in res.boxes:
            cls = int(box.cls[0])
            label = names.get(cls, str(cls)) if isinstance(names, dict) else names[cls]
            if label not in labels:
                continue
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            out.append(
                Detection(
                    label=label,
                    confidence=float(box.conf[0]),
                    bbox=(x1, y1, x2, y2),
                    center=((x1 + x2) / 2, (y1 + y2) / 2),
                    depth_m=None,
                )
            )
        return out
