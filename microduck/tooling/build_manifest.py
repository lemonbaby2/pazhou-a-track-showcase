"""生成 microduck/MANIFEST.csv：逐文件清单（相对路径 / 字节 / SHA-256 / 来源）。

用法：python microduck/tooling/build_manifest.py
MANIFEST.csv 自身不列入，避免自引用。
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

MOD = Path(__file__).resolve().parents[1]
OUT = MOD / "MANIFEST.csv"

SOURCE_MAP = [
    ("src/", "Gitee duckf--the-playful-duck / 短跑任务配置"),
    ("scripts/", "Gitee duckf--the-playful-duck / 实验脚本"),
    ("data/", "Gitee duckf--the-playful-duck / 短跑指标 JSON"),
    ("figs/", "Gitee duckf--the-playful-duck / 论文图"),
    ("checkpoints/", "Gitee duckf--the-playful-duck / 检查点"),
    ("videos/", "Gitee duckf--the-playful-duck / 短跑录像"),
    ("docs/", "Gitee duckf--the-playful-duck / 硬件与协议文档"),
    ("papers/", "Gitee duckf--the-playful-duck / 双栏论文稿"),
    ("course/optimization/", "Task8 控制层优化实验（2026-11-04）"),
    ("course/notebooks/", "Datawhale task3/notebooks 00-09"),
    ("course/validation/", "Datawhale task3/validation + execution"),
    ("course/videos/", "Datawhale task3/videos 精选 17 段"),
    ("course/logs/", "Datawhale task3/logs 原始运行日志"),
    ("course/site_src/", "Datawhale task3 站点源码"),
    ("course/upstream-docs/", "Datawhale 课程说明 + task1/task2 原件"),
    ("course/", "Gitee duckf--the-playful-duck / 课程归档"),
    ("paper-agent/", "本机 paper-agent 知识库与写作脚本"),
    ("tooling/lesson-scripts/", "本机 microduck_task 执行与修补脚本"),
    ("tooling/lightnav-probe/", "本机 duck-opt 探针与 18 组原始报告"),
]


def source_of(rel: str) -> str:
    for prefix, label in SOURCE_MAP:
        if rel.startswith(prefix):
            return label
    return "本轮封装新增（总索引 / 指标 / 建议 / 清单）"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


rows = []
for path in sorted(MOD.rglob("*")):
    if not path.is_file():
        continue
    rel = path.relative_to(MOD).as_posix()
    if rel == "MANIFEST.csv":
        continue
    rows.append({
        "path": rel,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "top_dir": rel.split("/", 1)[0] if "/" in rel else "[模块根]",
        "source": source_of(rel),
    })

with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["path", "bytes", "sha256", "top_dir", "source"])
    w.writeheader()
    w.writerows(rows)

total = sum(r["bytes"] for r in rows)
print(f"MANIFEST.csv: {len(rows)} 文件 / {total/1048576:.2f} MB")
by_dir: dict[str, list] = {}
for r in rows:
    by_dir.setdefault(r["top_dir"], []).append(r["bytes"])
for k, v in sorted(by_dir.items(), key=lambda kv: -sum(kv[1])):
    print(f"  {k:28s} {len(v):4d} 文件  {sum(v)/1048576:8.2f} MB")
