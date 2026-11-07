"""采集器与质检器单元测试（纯标准库，不碰真机也不依赖仿真渲染）。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from bev.dataset import (
    EpisodeRecorder,
    QCConfig,
    check_episode,
    iter_episodes,
    validate_dataset,
    write_report,
)


def _rec(root: Path) -> EpisodeRecorder:
    return EpisodeRecorder(root=root, task="beverage_service", fps=30.0, operator="tester")


def _write_ep(rec: EpisodeRecorder, n: int = 30, dt: float = 1 / 30.0,
              static: bool = False, success: bool = True) -> None:
    rec.start_episode("把第 1 瓶饮品放到客人桌面")
    for i in range(n):
        k = 0.0 if static else i * 0.01
        rec.add_frame([k, k * 0.5, k * 0.2, 0.0, 1.0], t=i * dt)
    rec.end_episode(success=success)


def test_recorder_writes_expected_tree(tmp_path: Path):
    rec = _rec(tmp_path)
    _write_ep(rec)
    assert (tmp_path / "meta" / "info.json").exists()
    assert (tmp_path / "meta" / "episodes.jsonl").exists()
    assert (tmp_path / "meta" / "tasks.jsonl").exists()
    d = tmp_path / "episodes" / "episode_000000"
    assert (d / "frames.jsonl").exists()
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    assert meta["num_frames"] == 30
    assert meta["success"] is True
    assert meta["frames_sha256"]
    assert abs(meta["duration_s"] - 29 / 30) < 1e-2   # 落盘保留 3 位小数


def test_index_continues_across_instances(tmp_path: Path):
    _write_ep(_rec(tmp_path), n=5)
    _write_ep(_rec(tmp_path), n=5)
    names = [p.name for p in iter_episodes(tmp_path)]
    assert names == ["episode_000000", "episode_000001"]


def test_dimension_mismatch_raises(tmp_path: Path):
    rec = _rec(tmp_path)
    rec.start_episode("x")
    rec.add_frame([0.0, 0.0, 0.0, 0.0, 0.0])
    with pytest.raises(ValueError):
        rec.add_frame([0.0, 0.0])


def test_action_autoderive(tmp_path: Path):
    rec = _rec(tmp_path)
    rec.start_episode("x")
    rec.add_frame([0.0, 0.0], t=0.0)
    rec.add_frame([1.0, 2.0], t=1 / 30)
    rec.end_episode()
    frames = [json.loads(l) for l in
              (tmp_path / "episodes" / "episode_000000" / "frames.jsonl").read_text("utf-8").splitlines()]
    assert frames[0]["action"] == [0.0, 0.0]
    assert frames[1]["action"] == [1.0, 2.0]


def test_clean_episode_passes(tmp_path: Path):
    _write_ep(_rec(tmp_path))
    d = next(iter_episodes(tmp_path))
    issues = check_episode(d, QCConfig(fps=30.0, min_episodes=1))
    assert [i for i in issues if i.is_error] == []


def test_static_episode_warns(tmp_path: Path):
    _write_ep(_rec(tmp_path), static=True)
    d = next(iter_episodes(tmp_path))
    codes = {i.code for i in check_episode(d, QCConfig(fps=30.0))}
    assert "W_STATIC" in codes


def test_too_long_episode_errors(tmp_path: Path):
    _write_ep(_rec(tmp_path), n=40, dt=2.0)
    d = next(iter_episodes(tmp_path))
    codes = {i.code for i in check_episode(d, QCConfig(fps=0.5, max_duration_s=30.0))}
    assert "E_LONG" in codes


def test_time_backwards_errors(tmp_path: Path):
    rec = _rec(tmp_path)
    rec.start_episode("x")
    rec.add_frame([0.0, 0.0], t=0.0)
    rec.add_frame([0.1, 0.0], t=1.0)
    rec.add_frame([0.2, 0.0], t=0.5)   # 回退
    rec.end_episode()
    d = next(iter_episodes(tmp_path))
    codes = {i.code for i in check_episode(d, QCConfig(fps=1.0))}
    assert "E_TIME_BACK" in codes


def test_empty_episode_errors(tmp_path: Path):
    p = tmp_path / "episodes" / "episode_000000"
    p.mkdir(parents=True)
    (p / "frames.jsonl").write_text("", encoding="utf-8")
    (p / "meta.json").write_text("{}", encoding="utf-8")
    codes = {i.code for i in check_episode(p, QCConfig())}
    assert "E_EMPTY" in codes


def test_validate_dataset_and_report(tmp_path: Path):
    _write_ep(_rec(tmp_path))
    _write_ep(_rec(tmp_path), static=True)
    rep = validate_dataset(tmp_path, QCConfig(fps=30.0, min_episodes=1), verbose=False)
    assert rep["episodes"] == 2
    assert rep["failed"] == 0
    assert rep["ok"] is True
    p = write_report(rep, tmp_path / "qc.json")
    assert json.loads(p.read_text(encoding="utf-8"))["episodes"] == 2


def test_low_episode_count_blocks_ok(tmp_path: Path):
    _write_ep(_rec(tmp_path))
    rep = validate_dataset(tmp_path, QCConfig(fps=30.0, min_episodes=50), verbose=False)
    assert rep["ok"] is False
    assert rep["dataset_warnings"]
