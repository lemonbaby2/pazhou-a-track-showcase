"""托盘姿态监控：端盘配送阶段的稳定性判据。

比赛要求「持续夹稳托盘、保持托盘不倾斜」，所以把倾角作为一等指标：
- 警告阈值（warn）：提前减速/微调；
- 限制阈值（limit）：判定失败，触发恢复（重新调平）。

注意：判定用「自上次复位以来的峰值」，而不是最后一帧的瞬时值——
否则导航途中的瞬时倾斜会在到达时被最后一步覆盖，漏判。
"""

from __future__ import annotations


class TrayMonitor:
    def __init__(self, limit_deg: float = 8.0, warn_deg: float = 5.0):
        self.limit_deg = float(limit_deg)
        self.warn_deg = float(warn_deg)
        self.tilt_deg = 0.0
        self.peak_deg = 0.0
        self.max_tilt_deg = 0.0
        self.trips = 0

    def update(self, tilt_deg: float) -> None:
        self.tilt_deg = float(tilt_deg)
        a = abs(self.tilt_deg)
        self.peak_deg = max(self.peak_deg, a)
        self.max_tilt_deg = max(self.max_tilt_deg, a)
        if a > self.limit_deg:
            self.trips += 1

    @property
    def exceeded(self) -> bool:
        return self.peak_deg > self.limit_deg

    @property
    def warning(self) -> bool:
        return self.warn_deg < self.peak_deg <= self.limit_deg

    def reset(self) -> None:
        self.tilt_deg = 0.0
        self.peak_deg = 0.0
