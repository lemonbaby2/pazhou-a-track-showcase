"""真机示教数据的落盘与质检（零第三方依赖）。

为什么不直接用 LeRobot 的 ``lerobot-record``？两条路各有位置：

* **路径 A（推荐，时间够时）**：直接用官方 ``lerobot-record`` 采，格式天然是
  LeRobotDataset，训练零适配。代价是要装 torch / lerobot（几百 MB）且必须
  实现一个 ``Robot`` 适配类。
* **路径 B（本模块，备赛保底）**：比赛现场网络与依赖不可控，用纯标准库把轨迹
  逐帧落成 JSONL + 元数据，先把数据**留下来**；训练前再按
  ``docs/真机数据采集SOP.md`` 转成 LeRobot 格式。

两条路的**采集原则完全一样**：一条 episode 只做一个完整子技能、5~15 秒、
动作连续、附带成功标记。本模块同时提供质检器，把"采完才发现数据废了"提前到
"采完立刻知道"。

目录结构（自描述，便于人工抽查）::

    <root>/
      meta/info.json              # 任务、帧率、相机、代码 commit、状态/动作语义
      meta/tasks.jsonl            # 去重后的语言指令
      meta/episodes.jsonl         # 每条 episode 的索引与校验和
      episodes/episode_000000/
        frames.jsonl              # 逐帧 t / state / action
        meta.json                 # 指令、成功标记、采集人、环境标签
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

SCHEMA_VERSION = "1.0"

STATE_LAYOUT = "state = [x_m, y_m, yaw_rad, tray_tilt_deg, holding(0/1), arm_idx]；真机换成关节角(rad)+夹爪(0~1)"
ACTION_LAYOUT = "action = state[t+1] - state[t] 的第 0/1/2/3 维差分，holding 与 arm_idx 取目标绝对值"


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #
def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_commit(start: Path) -> str:
    """尽力取当前代码 commit；取不到返回 ``unknown``（不抛异常）。"""
    try:
        out = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _f(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return float("nan")
    return v


# --------------------------------------------------------------------------- #
# 采集
# --------------------------------------------------------------------------- #
class EpisodeRecorder:
    """把一条条示教轨迹写进仓库外的数据目录。

    ``root`` 建议放在大容量盘上并加进 ``.gitignore``：视频与轨迹不应进 git。
    """

    def __init__(
        self,
        root: str | Path,
        task: str,
        fps: float = 30.0,
        cameras: Sequence[str] = ("front",),
        operator: str = "",
        extra_meta: Optional[Dict[str, Any]] = None,
    ):
        self.root = Path(root)
        self.task = task
        self.fps = float(fps)
        self.cameras = tuple(cameras)
        self.operator = operator
        self.extra_meta = dict(extra_meta or {})

        self._idx = -1
        self._dir: Optional[Path] = None
        self._fh = None
        self._n_frames = 0
        self._t0: Optional[float] = None
        self._last_t = 0.0
        self._dim: Optional[int] = None
        self._prev_state: Optional[List[float]] = None

        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "meta").mkdir(exist_ok=True)
        (self.root / "episodes").mkdir(exist_ok=True)
        self._idx = self._scan_last_index()
        self._write_info()

    def _scan_last_index(self) -> int:
        """接着已有数据往后编，避免多次运行互相覆盖。"""
        last = -1
        for d in (self.root / "episodes").iterdir():
            name = d.name
            if d.is_dir() and name.startswith("episode_"):
                try:
                    last = max(last, int(name.split("_", 1)[1]))
                except ValueError:
                    continue
        return last

    # ---------- 元数据 ----------
    def _write_info(self) -> None:
        info = self.root / "meta" / "info.json"
        if info.exists():
            return
        payload = {
            "schema_version": SCHEMA_VERSION,
            "task": self.task,
            "fps": self.fps,
            "cameras": list(self.cameras),
            "created_at": _now_iso(),
            "code_commit": code_commit(self.root),
            "state_layout": STATE_LAYOUT,
            "action_layout": ACTION_LAYOUT,
            **self.extra_meta,
        }
        info.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_jsonl(self, rel: str, rec: Dict[str, Any]) -> None:
        p = self.root / "meta" / rel
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---------- 生命周期 ----------
    def start_episode(self, instruction: str, labels: Optional[Dict[str, Any]] = None) -> Path:
        if self._fh is not None:
            raise RuntimeError("上一条 episode 还没 end_episode()")
        self._idx += 1
        self._dir = self.root / "episodes" / ("episode_%06d" % self._idx)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._fh = open(self._dir / "frames.jsonl", "w", encoding="utf-8")
        self._n_frames = 0
        self._t0 = None
        self._last_t = 0.0
        self._dim = None
        self._prev_state = None

        meta = {
            "episode_index": self._idx,
            "instruction": instruction,
            "task": self.task,
            "fps": self.fps,
            "cameras": list(self.cameras),
            "operator": self.operator,
            "started_at": _now_iso(),
            "labels": dict(labels or {}),
        }
        (self._dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._append_jsonl("tasks.jsonl", {"instruction": instruction, "task": self.task})
        return self._dir

    def add_frame(
        self,
        state: Sequence[float],
        action: Optional[Sequence[float]] = None,
        t: Optional[float] = None,
    ) -> None:
        """写一帧。``action`` 省略时按相邻状态差分自动生成（示教回放常用）。"""
        if self._fh is None:
            raise RuntimeError("先调用 start_episode()")
        st = [_f(v) for v in state]
        if self._dim is None:
            self._dim = len(st)
        elif len(st) != self._dim:
            raise ValueError("state 维度在 episode 内不一致：%d != %d" % (len(st), self._dim))

        if t is None:
            t = self._last_t + 1.0 / self.fps
        t = float(t)
        if self._t0 is None:
            self._t0 = t

        if action is None:
            if self._prev_state is None:
                act = [0.0] * len(st)
            else:
                act = [st[i] - self._prev_state[i] for i in range(len(st))]
        else:
            act = [_f(v) for v in action]
            if len(act) != len(st):
                raise ValueError("action 维度 %d 与 state 维度 %d 不一致" % (len(act), len(st)))

        rec = {"t": round(t - self._t0, 4), "state": st, "action": act}
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._n_frames += 1
        self._last_t = t
        self._prev_state = st

    def end_episode(self, success: bool = True, note: str = "") -> Dict[str, Any]:
        if self._fh is None or self._dir is None:
            raise RuntimeError("没有正在录制的 episode")
        self._fh.close()
        self._fh = None

        meta_p = self._dir / "meta.json"
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        frames_p = self._dir / "frames.jsonl"
        meta.update(
            {
                "success": bool(success),
                "note": note,
                "num_frames": self._n_frames,
                "duration_s": round(self._last_t - (self._t0 or 0.0), 3),
                "finished_at": _now_iso(),
                "frames_sha256": _sha256_file(frames_p) if frames_p.exists() else "",
            }
        )
        meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self._append_jsonl("episodes.jsonl", {k: meta[k] for k in (
            "episode_index", "instruction", "success", "num_frames",
            "duration_s", "started_at", "frames_sha256")})
        self._dir = None
        return meta

    def close(self) -> None:
        if self._fh is not None:
            self.end_episode(success=False, note="录制被中断")

    def __enter__(self) -> "EpisodeRecorder":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


# --------------------------------------------------------------------------- #
# 质检
# --------------------------------------------------------------------------- #
@dataclass
class QCConfig:
    fps: Optional[float] = None      # None = 由时间戳自动推断（真机固定 30Hz，仿真按源采样率）
    min_duration_s: float = 1.0
    max_duration_s: float = 30.0
    max_gap_ratio: float = 3.0        # 相邻帧间隔超过 N × 1/fps 记为丢帧
    min_action_std: float = 1e-3      # 动作近乎不动 → 无效示教
    spike_factor: float = 8.0         # 单帧动作跳变超过 N × 中位绝对动作 → 可疑
    spike_abs: float = 0.35           # 且绝对值也要超过这个阈值（米/弧度量级）
    joint_limit_rad: Optional[float] = None   # 真机关节角粗限位(rad)，防"把度当弧度"；仿真数据留 None 关闭
    gripper_range: Optional[Tuple[float, float]] = (0.0, 1.0)  # 夹爪维度取值范围；None 关闭
    min_episodes: int = 20            # 单任务建议最低条数，低于它给出 warn


@dataclass
class Issue:
    code: str
    severity: str  # "error" | "warn"
    msg: str

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


def iter_episodes(root: str | Path) -> Iterator[Path]:
    ep_root = Path(root) / "episodes"
    if not ep_root.exists():
        return
    for d in sorted(ep_root.iterdir()):
        if d.is_dir() and (d / "frames.jsonl").exists():
            yield d


def _load_episode(d: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    meta = {}
    mp = d / "meta.json"
    if mp.exists():
        try:
            meta = json.loads(mp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {"_meta_error": True}
    frames: List[Dict[str, Any]] = []
    for line in (d / "frames.jsonl").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            frames.append(json.loads(line))
        except json.JSONDecodeError:
            frames.append({"__bad__": True})
    return meta, frames


def check_episode(d: Path, cfg: QCConfig) -> List[Issue]:
    """对单条 episode 做全套规则检查，返回问题列表（空 = 通过）。"""
    issues: List[Issue] = []
    meta, frames = _load_episode(d)

    if meta.get("_meta_error"):
        issues.append(Issue("E_META", "error", "meta.json 损坏（JSON 解析失败）"))
    if not frames:
        issues.append(Issue("E_EMPTY", "error", "frames.jsonl 为空"))
        return issues
    if any(f.get("__bad__") for f in frames):
        issues.append(Issue("E_FRAME_JSON", "error", "存在无法解析的帧"))

    good = [f for f in frames if "state" in f and "action" in f]
    if len(good) < 2:
        issues.append(Issue("E_TOO_FEW", "error", "有效帧不足 2 帧"))
        return issues

    dims = {len(f["state"]) for f in good} | {len(f["action"]) for f in good}
    if len(dims) > 1:
        issues.append(Issue("E_DIM", "error", "state/action 维度不一致：%s" % sorted(dims)))
    dim = dims.pop() if len(dims) == 1 else 0

    # 时长
    ts = [_f(f.get("t", 0.0)) for f in good]
    duration = ts[-1] - ts[0]
    if duration < cfg.min_duration_s:
        issues.append(Issue("W_SHORT", "warn", "时长 %.2fs 偏短（<%.1fs），示教信息量不足"
                            % (duration, cfg.min_duration_s)))
    if duration > cfg.max_duration_s:
        issues.append(Issue("E_LONG", "error", "时长 %.2fs 超上限 %.0fs，应拆成多个子技能"
                            % (duration, cfg.max_duration_s)))

    # 丢帧 / 时间戳回退
    dts = [b - a for a, b in zip(ts, ts[1:]) if b > a]
    fps = cfg.fps
    if fps is None:
        med = statistics.median(dts) if dts else 1.0 / 30.0
        fps = (1.0 / med) if med > 0 else 30.0
    dt = 1.0 / fps
    gaps = 0
    for a, b in zip(ts, ts[1:]):
        a_d, b_d = round(a, 6), round(b, 6)
        if b_d <= a_d:
            issues.append(Issue("E_TIME_BACK", "error", "时间戳非递增（%.3f → %.3f）" % (a_d, b_d)))
            break
        if (b_d - a_d) > cfg.max_gap_ratio * dt:
            gaps += 1
    if gaps:
        rate = gaps / max(1, len(ts) - 1)
        sev = "error" if rate > 0.05 else "warn"
        issues.append(Issue("E_GAP" if sev == "error" else "W_GAP", sev,
                            "丢帧 %d 处（%.1f%% 的帧间隔 >%@ %.0fms）"
                            % (gaps, rate * 100, cfg.max_gap_ratio, dt * 1000)))

    # 动作有效性
    flat = [v for f in good for v in f["action"]]
    try:
        astd = statistics.pstdev(flat)
    except statistics.StatisticsError:
        astd = 0.0
    if astd < cfg.min_action_std:
        issues.append(Issue("W_STATIC", "warn", "动作几乎不变（std=%.2e），像空录或死帧" % astd))

    for i in range(dim):
        raw = [_f(f["action"][i]) for f in good]
        # 二值维度（夹爪开合、holding 标志）跳变是离散事件，不是异常
        if set(raw) <= {0.0, 1.0, -1.0}:
            continue
        col = [abs(v) for v in raw]
        med = statistics.median(col) or 0.0
        worst = max(col)
        if worst > max(cfg.spike_abs, cfg.spike_factor * med):
            issues.append(Issue("W_SPIKE", "warn",
                                "第 %d 维动作出现跳变 %.3f（中位 %.3f），检查标定或丢帧" % (i, worst, med)))

    # 关节/夹爪量纲合理性（真机数据才开，仿真或抽象动作空间会误报）
    if cfg.joint_limit_rad is not None and dim >= 1:
        for i in range(dim):
            mx = max(abs(_f(f["state"][i])) for f in good)
            if mx > cfg.joint_limit_rad:
                issues.append(Issue("W_UNIT", "warn",
                                    "第 %d 维状态最大 %.2f 超过 %.1f rad，疑似把度当弧度" % (i, mx, cfg.joint_limit_rad)))
                break
    if cfg.gripper_range is not None and dim >= 2:
        lo, hi = cfg.gripper_range
        g = [_f(f["state"][dim - 1]) for f in good]
        if min(g) < lo - 1e-6 or max(g) > hi + 1e-6:
            issues.append(Issue("W_GRIPPER", "warn",
                                "最后一维（夹爪）取值 [%.2f, %.2f] 越出 [%.1f, %.1f]" % (min(g), max(g), lo, hi)))

    # 标记
    if "success" not in meta:
        issues.append(Issue("W_NO_SUCCESS", "warn", "meta.json 缺 success 字段，训练集无法筛成败"))
    if not meta.get("instruction"):
        issues.append(Issue("W_NO_INSTR", "warn", "缺语言指令，VLA 训练无法用"))
    return issues


def validate_dataset(
    root: str | Path, cfg: Optional[QCConfig] = None, verbose: bool = True
) -> Dict[str, Any]:
    """扫描整个数据集，产出可写盘、可进 CI 的报告。"""
    cfg = cfg or QCConfig()
    root = Path(root)
    per_ep: List[Dict[str, Any]] = []
    counts = {"error": 0, "warn": 0}

    for d in iter_episodes(root):
        issues = check_episode(d, cfg)
        e = sum(1 for i in issues if i.is_error)
        w = len(issues) - e
        counts["error"] += e
        counts["warn"] += w
        per_ep.append({
            "episode": d.name,
            "ok": e == 0,
            "errors": e,
            "warns": w,
            "issues": [{"code": i.code, "severity": i.severity, "msg": i.msg} for i in issues],
        })
        if verbose:
            flag = "PASS" if e == 0 else "FAIL"
            print("[%s] %s  err=%d warn=%d" % (flag, d.name, e, w))
            for i in issues:
                print("        %-12s %s" % (i.code, i.msg))

    n = len(per_ep)
    passed = sum(1 for p in per_ep if p["ok"])
    dataset_warns: List[str] = []
    if n and n < cfg.min_episodes:
        dataset_warns.append("条数 %d 低于建议下限 %d（单任务建议 ≥50 条，50 条干净数据优于 200 条单一配置）"
                             % (n, cfg.min_episodes))

    report = {
        "root": str(root),
        "checked_at": _now_iso(),
        "config": cfg.__dict__,
        "episodes": n,
        "passed": passed,
        "failed": n - passed,
        "errors": counts["error"],
        "warns": counts["warn"],
        "dataset_warnings": dataset_warns,
        "detail": per_ep,
        "ok": n > 0 and counts["error"] == 0 and not dataset_warns,
    }
    if verbose:
        print("\n合计 %d 条：通过 %d，失败 %d（error %d / warn %d）"
              % (n, passed, n - passed, counts["error"], counts["warn"]))
        for w in dataset_warns:
            print("[数据集] %s" % w)
    return report


def write_report(report: Dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
