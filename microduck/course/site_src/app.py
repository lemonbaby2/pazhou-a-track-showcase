"""MicroDuck 03-Notebook 成果站 —— FastAPI 后端.

职责:
  1. 静态托管: index.html / videos / validation / notebooks / logs
  2. 只读 API: 任务清单、单任务详情、视频索引、健康检查、运行摘要
  3. SQLite: 启动时把 validation/*.json 与 videos/*.mp4 汇总入库, 供前端与外部调用

启动:
  uvicorn app:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "runs.db"
VIDEO_DIR = BASE / "videos"
VALID_DIR = BASE / "validation"
LOG_DIR = BASE / "logs"

TASK_META = {
    "00": ("MuJoCo 策略控制 HelloWorld", "HelloWorld", "基础控制链路"),
    "01": ("篮球平衡 PPO/ONNX/BPU", "Basketball", "PPO 冒烟 + ONNX + parity 校验"),
    "02": ("浏览器物理扰动回放", "Perturbation", "walking + 外力扰动"),
    "03": ("高跷行走课程与 ONNX", "Stilt", "25cm 高跷策略"),
    "04": ("摆动旋转 ONNX", "Swing", "摆锤泵能"),
    "05": ("球平衡 FastSAC", "BallBalance", "FastSAC + checkpoint 审计"),
    "06": ("梯面攀爬接触与部署", "Ladder", "climber/getup 双策略攀爬"),
    "07": ("RDK 网页与多策略验收", "RDK-BPU", "无板未验收"),
    "08": ("LightNav0 视觉语言导航", "LightNav", "三场景 VLM 导航"),
    "09": ("跨缝跳跃 PPO", "LongJump", "续训 + 部署 parity"),
}


def _video_key(stem: str) -> str | None:
    """把视频文件名映射回任务编号."""
    s = stem.lower()
    if s.startswith("lightnav"):
        return "08"
    if s.startswith("long_jump"):
        return "09"
    table = [
        ("basketball", "01"),
        ("perturbation", "02"),
        ("walking", "02"),
        ("stilt", "03"),
        ("swing", "04"),
        ("ball_balance", "05"),
        ("ladder", "06"),
    ]
    for key, tid in table:
        if s.startswith(key):
            return tid
    return None


def _probe_duration(path: Path) -> float | None:
    """不依赖 ffprobe: 读 MP4 mvhd 时长（兼容 moov 在头或尾）."""
    try:
        size = path.stat().st_size
        chunks = []
        with path.open("rb") as fh:
            chunks.append(fh.read(min(size, 1 << 20)))
            if size > (1 << 21):
                fh.seek(max(0, size - (1 << 20)))
                chunks.append(fh.read(1 << 20))
        for buf in chunks:
            idx = buf.find(b"mvhd")
            if idx < 0:
                continue
            version = buf[idx + 4]
            if version == 0:
                timescale = int.from_bytes(buf[idx + 16:idx + 20], "big")
                duration = int.from_bytes(buf[idx + 20:idx + 24], "big")
            else:
                timescale = int.from_bytes(buf[idx + 24:idx + 28], "big")
                duration = int.from_bytes(buf[idx + 28:idx + 36], "big")
            if timescale:
                return round(duration / timescale, 2)
        return None
    except Exception:
        return None


def build_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS videos;
        DROP TABLE IF EXISTS tasks;
        CREATE TABLE tasks(
            task_id TEXT PRIMARY KEY,
            title TEXT, code TEXT, note TEXT,
            video_count INTEGER, total_seconds REAL, updated_at TEXT
        );
        CREATE TABLE videos(
            name TEXT PRIMARY KEY, task_id TEXT, path TEXT,
            size_bytes INTEGER, duration_s REAL
        );
        """
    )
    rows: dict[str, list] = {}
    if VIDEO_DIR.is_dir():
        for mp4 in sorted(VIDEO_DIR.glob("*.mp4")):
            tid = _video_key(mp4.stem) or "--"
            dur = _probe_duration(mp4)
            size = mp4.stat().st_size
            cur.execute(
                "INSERT OR REPLACE INTO videos VALUES (?,?,?,?,?)",
                (mp4.name, tid, f"videos/{mp4.name}", size, dur),
            )
            rows.setdefault(tid, []).append(dur or 0.0)
    for tid, (title, code, note) in TASK_META.items():
        durs = rows.get(tid, [])
        cur.execute(
            "INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?,datetime('now'))",
            (tid, title, code, note, len(durs), round(sum(durs), 1)),
        )
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    build_db()
    yield


app = FastAPI(title="MicroDuck 03-Notebook", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)

for sub, mount in (("videos", "videos"), ("validation", "validation"),
                   ("notebooks", "notebooks"), ("logs", "logs"), ("duck", "duck")):
    p = BASE / sub
    if p.is_dir():
        app.mount(f"/{mount}", StaticFiles(directory=str(p)), name=mount)


@app.get("/api/duck/sprint")
def duck_sprint():
    """MicroDuck 短跑实验室：训练曲线 + 实测速度（第十一章数据源）。"""
    out = {}
    for name in ("sprint_metrics.json", "sprint_speed.json"):
        p = BASE / "duck" / name
        if p.is_file():
            try:
                out[name.replace(".json", "")] = json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                out[name.replace(".json", "")] = {"error": str(exc)}
    if not out:
        raise HTTPException(status_code=404, detail="duck/sprint_*.json not synced yet")
    return out


@app.get("/api/health")
def health():
    return {"status": "ok", "videos": len(list(VIDEO_DIR.glob("*.mp4"))) if VIDEO_DIR.is_dir() else 0}


@app.get("/api/tasks")
def list_tasks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tasks = [dict(r) for r in conn.execute("SELECT * FROM tasks ORDER BY task_id")]
    for t in tasks:
        t["videos"] = [
            dict(r) for r in conn.execute(
                "SELECT name, path, size_bytes, duration_s FROM videos WHERE task_id=? ORDER BY name",
                (t["task_id"],),
            )
        ]
    conn.close()
    return {"count": len(tasks), "tasks": tasks}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"task {task_id} not found")
    task = dict(row)
    task["videos"] = [
        dict(r) for r in conn.execute("SELECT * FROM videos WHERE task_id=?", (task_id,))
    ]
    conn.close()
    return task


@app.get("/api/videos")
def list_videos(min_seconds: float = Query(0, ge=0)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [
        dict(r) for r in conn.execute(
            "SELECT * FROM videos WHERE COALESCE(duration_s,0) >= ? ORDER BY task_id, name",
            (min_seconds,),
        )
    ]
    conn.close()
    return {"count": len(rows), "min_seconds": min_seconds, "videos": rows}


@app.get("/api/summary")
def summary():
    conn = sqlite3.connect(DB_PATH)
    total_videos, total_s = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(duration_s),0) FROM videos"
    ).fetchone()
    two_min = conn.execute(
        "SELECT COUNT(*) FROM videos WHERE COALESCE(duration_s,0) >= 120"
    ).fetchone()[0]
    conn.close()
    validations = sorted(p.name for p in VALID_DIR.glob("*.json")) if VALID_DIR.is_dir() else []
    return {
        "videos_total": total_videos,
        "videos_2min_plus": two_min,
        "video_seconds_total": round(total_s or 0, 1),
        "validations": len(validations),
        "validation_files": validations,
        "notebooks": sorted(p.name for p in (BASE / "notebooks").glob("*.ipynb")),
        "logs": sorted(p.name for p in LOG_DIR.glob("*_execution.json")),
    }


@app.get("/")
def index():
    page = BASE / "index.html"
    if page.is_file():
        return FileResponse(page)
    return JSONResponse({"service": "microduck-task3", "api": "/api/tasks"}, status_code=200)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )
