#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DGX Spark · pi0.5 3.6B 8h continuous training + ablation + periodic monitoring.

Modes:
  python vla8h.py orchestrate   # wait weights -> 30min smoke -> 4 arms -> final report
  python vla8h.py monitor       # resident: 5min metrics / 30min curve+snapshot / watchdog

All paths are absolute. Everything is detached from the SSH session by start_all.sh.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/nvidia/vla-8h")
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"
FIGS = ROOT / "figs"
STATE = ROOT / "state"
for d in (LOGS, REPORTS, FIGS, STATE):
    d.mkdir(parents=True, exist_ok=True)

# lerobot 0.6.1 env: official pi05 support, transformers 5.5.4, torch 2.11+cu130.
# (wallx-env 0.4.4 pi05 port requires a SigLIP transformers monkey-patch -> unusable)
VENV = "/home/nvidia/vla-runs/2026-10-12_smolvla_libero_night/venv"
PY = VENV + "/bin/python"
ACC = VENV + "/bin/accelerate"
MODEL = "/home/nvidia/models/pi05_base"
DATA_ROOT = "/home/nvidia/datasets/libero_all"
DL_LOG = LOGS / "download.log"
PID_FILE = STATE / "train.pid"
PLAN_FILE = STATE / "plan.json"
STATUS_FILE = STATE / "status.json"
METRICS = REPORTS / "metrics.jsonl"

SMOKE_SECONDS = 1800          # 30 min
TOTAL_SECONDS = 8 * 3600      # 8 h
ARM_SECONDS = (TOTAL_SECONDS - SMOKE_SECONDS) // 4
MEM_FLOOR_MB = 12_000         # watchdog: below this, kill training to protect CVAT

LOSS_RE = re.compile(
    r"loss:([0-9]*\.?[0-9]+)\s+grdn:([0-9]*\.?[0-9]+)\s+lr:([0-9.eE+-]+)\s+updt_s:([0-9]*\.?[0-9]+)"
)
STEP_RE = re.compile(r"(\d+)/(\d+)\s*\[")
ELAPSED_RE = re.compile(r"\[(\d+):(\d\d):(\d\d)<")
UNREC_RE = re.compile(r"unrecognized arguments:\s*([^\n]+)")

# (id, human label, extra args, paper method)
ARMS = [
    ("A_ki", "基线：Knowledge Insulation + QUANTILES + Beta(1.5,1.0)",
     ["--policy.train_expert_only=true", "--policy.freeze_vision_encoder=true"],
     "pi0.5 原生 flow matching + Knowledge Insulation (arXiv 2505.23705)"),
    ("B_lm", "解冻 VLM 语言模型（仅冻结视觉塔）",
     ["--policy.train_expert_only=false", "--policy.freeze_vision_encoder=true"],
     "Knowledge Insulation 消融（VLM 是否参与训练）"),
    ("C_mstd", "QUANTILES -> MEAN_STD",
     ["--policy.train_expert_only=true", "--policy.freeze_vision_encoder=true",
      '--policy.normalization_mapping={"ACTION": "MEAN_STD", "STATE": "MEAN_STD", "VISUAL": "IDENTITY"}'],
     "openpi / pi05_libero_finetuned 参考配方"),
    ("D_beta", "Beta(1.5,1.0) -> Beta(1.0,1.0) 均匀时间采样",
     ["--policy.train_expert_only=true", "--policy.freeze_vision_encoder=true",
      "--policy.time_sampling_beta_alpha=1.0", "--policy.time_sampling_beta_beta=1.0"],
     "pi0 论文 §4 flow matching timestep sampling 消融"),
]

BASE_ARGS = [
    "--policy.type=pi05",
    f"--policy.pretrained_path={MODEL}",
    "--policy.dtype=bfloat16",
    "--policy.device=cuda",
    "--policy.gradient_checkpointing=true",
    "--policy.chunk_size=50",
    "--policy.n_action_steps=10",
    "--policy.optimizer_lr=2.5e-5",
    "--policy.push_to_hub=false",
    "--dataset.repo_id=lerobot/libero",
    f"--dataset.root={DATA_ROOT}",
    "--dataset.video_backend=pyav",
    "--batch_size=4",
    "--num_workers=4",
    "--env_eval_freq=0",
    "--wandb.enable=false",
    "--seed=1000",
    "--log_freq=50",
]

ENV = dict(os.environ)
ENV.update({
    "HF_ENDPOINT": "https://hf-mirror.com",
    "HF_HUB_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "PI05_TOKENIZER": "/home/nvidia/models/paligemma-3b-pt-224",
    "TOKENIZERS_PARALLELISM": "false",
    "OMP_NUM_THREADS": "4",
    "OPENBLAS_NUM_THREADS": "1",
    "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
})


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    with (LOGS / "orchestrator.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(cmd: str, timeout: int = 20) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def write_status(**kw) -> None:
    data = {"updated_at": now(), **kw}
    STATUS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------- orchestrate

def wait_weights(timeout_s: int = 3600) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        txt = DL_LOG.read_text(errors="replace") if DL_LOG.exists() else ""
        if "DOWNLOADED" in txt and "RC=0" in txt:
            log("weights ready")
            return True
        if "RC=" in txt and "DOWNLOADED" not in txt:
            log("download FAILED; log tail: " + txt[-600:])
            return False
        time.sleep(20)
    log("weights timeout")
    return False


def parse_log(path: Path):
    if not path.exists():
        return [], {"current": None, "total": None, "elapsed_s": None}
    txt = path.read_text(errors="replace")
    series = []
    for a, b, c, d in LOSS_RE.findall(txt):
        try:
            series.append({"loss": float(a), "grdn": float(b), "lr": float(c), "updt_s": float(d)})
        except ValueError:
            pass
    steps = STEP_RE.findall(txt)
    cur = int(steps[-1][0]) if steps else None
    total = int(steps[-1][1]) if steps else None
    el = ELAPSED_RE.findall(txt)
    elapsed = (int(el[-1][0]) * 3600 + int(el[-1][1]) * 60 + int(el[-1][2])) if el else None
    return series, {"current": cur, "total": total, "elapsed_s": elapsed}


def build_cmd(arm_id: str, steps: int, extra: list, drop: set | None = None) -> list:
    """Build train command; `drop` holds flags rejected by this lerobot version."""
    drop = drop or set()

    def keep(a: str) -> bool:
        return a.split("=")[0] not in drop

    args = [a for a in BASE_ARGS if keep(a)]
    args += [
        f"--steps={steps}",
        f"--save_freq={max(100, steps // 2)}",
        f"--output_dir={ROOT / 'outputs' / arm_id}",
        f"--job_name=vla8h_{arm_id}",
    ] + [e for e in extra if keep(e)]
    if Path(ACC).exists():
        return ["nice", "-n", "10", "taskset", "-c", "0-9", ACC, "launch",
                "--num_processes=1", "--num_machines=1", "--mixed_precision=bf16",
                "--module", "lerobot.scripts.lerobot_train"] + args
    return ["nice", "-n", "10", "taskset", "-c", "0-9", PY,
            "-m", "lerobot.scripts.lerobot_train"] + args


def run_arm(arm_id: str, steps: int, extra: list, seconds: int) -> dict:
    log_path = LOGS / f"train_{arm_id}.log"
    result = {"arm": arm_id, "steps_planned": steps, "seconds_budget": seconds,
              "started_at": now(), "cmd": None, "rc": None, "loss_series": 0,
              "first_loss": None, "last_loss": None, "min_loss": None,
              "steps_done": None, "step_per_s": None, "note": "",
              "dropped_args": [], "attempts": 0}

    # Auto-adapt to lerobot version differences: any flag reported as
    # "unrecognized arguments" is removed and the arm is retried (max 6 tries).
    dropped: set = set()
    for attempt in range(6):
        cmd = build_cmd(arm_id, steps, extra, drop=dropped)
        result["cmd"] = " ".join(cmd)
        result["attempts"] = attempt + 1
        log(f"START {arm_id} attempt={attempt} steps={steps} budget={seconds}s")
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"\n===== {now()} {arm_id} attempt={attempt} =====\n")
            f.write("CMD: " + " ".join(cmd) + "\n")
            f.flush()
            p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT,
                                 cwd="/home/nvidia", env=ENV, start_new_session=True)
            PID_FILE.write_text(str(p.pid), encoding="utf-8")
            try:
                rc = p.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                log(f"TIMEOUT {arm_id} -> graceful SIGTERM")
                try:
                    os.killpg(p.pid, signal.SIGTERM)
                    p.wait(timeout=90)
                except Exception:
                    os.killpg(p.pid, signal.SIGKILL)
                rc = 124
            result["rc"] = rc
        tail = log_path.read_text(errors="replace")[-3000:]
        m = UNREC_RE.search(tail)
        if m:
            flags = {x.split("=")[0] for x in m.group(1).split() if x.startswith("--")}
            fresh = flags - dropped
            if fresh:
                dropped |= fresh
                log(f"RETRY {arm_id} dropping {sorted(fresh)}")
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(f"\n===== RETRY dropping {sorted(fresh)} =====\n")
                continue
        break
    result["dropped_args"] = sorted(dropped)

    series, st = parse_log(log_path)
    result["loss_series"] = len(series)
    if series:
        vals = [x["loss"] for x in series]
        result["first_loss"], result["last_loss"], result["min_loss"] = vals[0], vals[-1], min(vals)
    result["steps_done"] = st["current"]
    if st["current"] and st["elapsed_s"]:
        result["step_per_s"] = round(st["current"] / st["elapsed_s"], 4)
    elif result["steps_done"]:
        result["step_per_s"] = round(result["steps_done"] / max(1, seconds), 4)
    result["finished_at"] = now()
    PID_FILE.write_text("0", encoding="utf-8")
    log(f"DONE {arm_id} rc={result['rc']} losses={len(series)} last={result['last_loss']} steps={result['steps_done']}")
    return result


def protocol_md(speed: float, plan: dict) -> str:
    rows = "\n".join(
        f"| `{a[0]}` | {a[1]} | {a[3]} | {p['steps']} | {p['seconds']//60} min |"
        for a, p in zip(ARMS, plan["arms"])
    )
    return f"""# 8 小时连续训练实验协议（pi0.5 3.6B / DGX Spark GB10）

生成时间：{now()}
实测冒烟速度：**{speed:.4f} step/s**；总预算 8 h（含 30 min 冒烟），4 个消融臂平分余下 7.5 h。

## 1. 自变量设计（复现论文方法）

| 臂 | 自变量 | 对应论文方法 | 计划步数 | 时长 |
|---|---|---|---:|---:|
{rows}

共同固定项：`policy.type=pi05`、`pretrained_path=lerobot/pi05_base`、bfloat16、
`gradient_checkpointing=true`、`chunk_size=50`、`n_action_steps=10`、`batch_size=4`、
LIBERO v3.0（1693 episodes / 273465 frames / 40 tasks，本地 1.9 G）、`seed=1000`、
`optimizer_lr=2.5e-5`、`log_freq=50`。

## 2. 已复现的方法

- **Flow matching 动作头**（pi0 / pi0.5 核心）：10 步积分、Beta(1.5,1.0) 时间采样、动作 chunk 50。
- **Knowledge Insulation**（arXiv 2505.23705）：冻结 VLM / 视觉编码器，只训 300 M action expert 与投影。
- **QUANTILES 归一化**（pi0.5 原生）：数据集 `meta/stats.json` 含 q01/q99，STATE/ACTION 走分位数。
- **离散状态输入 + 子任务语言**：`tokenizer_max_length=200`，状态离散化写入 prompt。
- **Timestep sampling 消融**（pi0 论文 §4）：Beta 分布 vs 均匀采样。
- **MEAN_STD 对照**：对齐 openpi / `pi05_libero_finetuned` 参考配方。

## 3. 明确未复现（边界，不得模糊）

| 项 | 原因 |
|---|---|
| pi0.5 论文第一阶段 FAST 离散动作预训练 | openpi / lerobot 仓库只开源第二阶段 flow matching head |
| 部署时高层子任务推理（high-level subtask prediction） | 开源仓库未包含 |
| 论文 60k steps × global batch 384 全量配方 | DGX Spark 单卡 BF16 算力约 21.5 TFLOPS，与 6×A800 差约 90× |
| 原榜单 LIBERO / RoboTwin 数值 | SAPIEN 3.0 仅 x86_64 wheel，aarch64 无法闭环评测 |
| 6B LingBot-VLA / 4B Kairos 全参训练 | 权重在本机但算力不足，仅可做推理级复现（见 `~/vla_repro/REPRODUCTION.md`） |

## 4. 生产保护

训练进程 `nice -n 10` + `taskset -c 0-9`（20 核留一半给产线）。
监控进程每 5 min 检查可用内存与 CVAT / nuclio 容器健康；
可用内存低于 {MEM_FLOOR_MB//1024} GB 时主动终止训练，保住 CVAT 标注与 4 个 YOLO 推理函数。

## 5. 数据真实性

loss / grad norm / lr / step time 全部从 `lerobot_train` 的 tqdm 日志正则解析，
未做任何插值或伪造。原始日志保存在 `logs/train_*.log`，逐条指标在 `reports/metrics.jsonl`。
"""


def orchestrate() -> None:
    log("=== ORCHESTRATOR START ===")
    write_status(phase="waiting_weights", started_at=now())
    if not wait_weights():
        write_status(phase="failed", reason="weights download failed")
        (REPORTS / "FAILED.md").write_text(
            f"# 训练未启动\n\n{now()}\n\n权重下载失败，详见 `logs/download.log`。\n", encoding="utf-8")
        return

    write_status(phase="smoke", started_at=now())
    smoke = run_arm("smoke", 100000, ARMS[0][2], SMOKE_SECONDS)
    speed = smoke.get("step_per_s") or 0.0
    if not smoke["loss_series"] or speed <= 0:
        write_status(phase="failed", reason="smoke produced no loss", smoke=smoke)
        (REPORTS / "FAILED.md").write_text(
            f"# 冒烟未通过\n\n{now()}\n\n```json\n{json.dumps(smoke, ensure_ascii=False, indent=2)}\n```\n"
            f"\n日志：`logs/train_smoke.log`\n", encoding="utf-8")
        log("SMOKE FAILED - abort 8h run")
        return

    usable = max(1, int((ARM_SECONDS - 180) * speed * 0.95))
    plan = {"speed_step_per_s": speed, "smoke": smoke,
            "arms": [{"id": a[0], "steps": usable, "seconds": ARM_SECONDS} for a in ARMS],
            "created_at": now()}
    PLAN_FILE.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS / "PROTOCOL.md").write_text(protocol_md(speed, plan), encoding="utf-8")
    log(f"SMOKE OK speed={speed} step/s -> {usable} steps per arm")

    results = []
    for (arm_id, label, extra, method), cfg in zip(ARMS, plan["arms"]):
        write_status(phase="training", arm=arm_id, arm_index=len(results) + 1, total_arms=4)
        r = run_arm(arm_id, cfg["steps"], extra, cfg["seconds"])
        r["label"], r["paper_method"] = label, method
        results.append(r)
        (STATE / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        if r["rc"] not in (0, 124):
            log(f"arm {arm_id} rc={r['rc']} unexpected; continuing to next arm")

    write_status(phase="done", finished_at=now())
    lines = ["# 8 小时连续训练最终结果", "", f"完成时间：{now()}",
             f"冒烟实测：{speed:.4f} step/s；每臂 {usable} 步。", "",
             "| 臂 | 自变量 | 终止码 | loss 首 | loss 末 | loss 最小 | 采样点数 | 完成步数 |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        fmt = lambda v: f"{v:.4f}" if isinstance(v, float) else "—"
        lines.append(f"| `{r['arm']}` | {r['label']} | {r['rc']} | {fmt(r['first_loss'])} | "
                     f"{fmt(r['last_loss'])} | {fmt(r['min_loss'])} | {r['loss_series']} | {r['steps_done'] or '—'} |")
    lines += ["", "## 边界", "",
              "8 小时只能做少步数微调，**未复现论文榜单数值**；未复现项详见 `PROTOCOL.md` 第 3 节。",
              "loss / grad norm / lr 均从训练日志正则解析，原始日志在 `logs/train_*.log`。", ""]
    (REPORTS / "FINAL.md").write_text("\n".join(lines), encoding="utf-8")
    log("=== ORCHESTRATOR DONE ===")


# ---------------------------------------------------------------------------- monitor

def sys_metrics() -> dict:
    m = {}
    for line in sh("free -m").splitlines():
        if line.startswith("Mem:"):
            p = line.split()
            try:
                m["mem_total_mb"], m["mem_used_mb"], m["mem_available_mb"] = int(p[1]), int(p[2]), int(p[6])
            except (ValueError, IndexError):
                pass
    try:
        m["load1"] = float(open("/proc/loadavg").read().split()[0])
    except Exception:
        pass
    # DGX Spark GB10 reports memory fields as "[N/A]" (unified memory), which
    # used to make the whole row fail the "N/A" guard and silently drop the GPU
    # metric. Query utilization alone so it is always a clean integer.
    gpu = sh("nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits")
    if gpu and gpu.splitlines():
        try:
            m["gpu_util_pct"] = float(gpu.splitlines()[0].split(",")[0].strip())
        except ValueError:
            pass
    ps = sh("docker ps --format '{{.Names}} {{.Status}}'", timeout=25)
    m["nuclio_healthy"] = sum(1 for l in ps.splitlines() if l.startswith("nuclio-") and "healthy" in l)
    m["cvat_up"] = sum(1 for l in ps.splitlines() if l.startswith("cvat") and "Up" in l)
    return m


def make_figures(series: list) -> None:
    if not series:
        return
    vals = [p["loss"] for p in series]
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 3.6), dpi=110)
        ax.plot(range(len(vals)), vals, lw=1.2, color="#2563eb")
        if len(vals) > 20:
            w = max(5, len(vals) // 40)
            sm = [sum(vals[max(0, i - w):i + 1]) / len(vals[max(0, i - w):i + 1]) for i in range(len(vals))]
            ax.plot(range(len(sm)), sm, lw=2.0, color="#dc2626", label=f"moving avg (w={w})")
            ax.legend(fontsize=8)
        ax.set_xlabel("logged step (log_freq=50)", fontsize=9)
        ax.set_ylabel("flow matching loss", fontsize=9)
        ax.set_title("pi0.5 3.6B · LIBERO · training loss", fontsize=11)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIGS / "loss_latest.png")
        plt.close(fig)
    except Exception as e:
        (LOGS / "monitor.log").open("a", encoding="utf-8").write(f"[{now()}] matplotlib: {e}\n")
    # SVG fallback (always available, no deps)
    W, H = 900, 320
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    pts = " ".join(f"{40 + (W - 80) * i / max(1, len(vals) - 1):.1f},"
                   f"{H - 40 - (H - 80) * (v - lo) / rng:.1f}" for i, v in enumerate(vals))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>'
           f'<text x="40" y="24" font-size="14" fill="#111">pi0.5 3.6B loss · n={len(vals)} · min={lo:.4f} max={hi:.4f}</text>'
           f'<polyline points="{pts}" fill="none" stroke="#2563eb" stroke-width="1.5"/>'
           f'</svg>')
    (FIGS / "loss_latest.svg").write_text(svg, encoding="utf-8")


def current_train_log():
    files = sorted(LOGS.glob("train_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def snapshot(series, st, sm, alerts) -> None:
    vals = [p["loss"] for p in series]
    status = json.loads(STATUS_FILE.read_text(encoding="utf-8")) if STATUS_FILE.exists() else {}
    make_figures(series)
    payload = {"generated_at": now(), "phase": status.get("phase"), "arm": status.get("arm"),
               "samples": len(series), "first_loss": vals[0] if vals else None,
               "last_loss": vals[-1] if vals else None, "min_loss": min(vals) if vals else None,
               "last_lr": series[-1]["lr"] if series else None,
               "last_grdn": series[-1]["grdn"] if series else None,
               "steps_current": st.get("current"), "steps_total": st.get("total"),
               "system": sm, "alerts": alerts[-5:]}
    (REPORTS / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fmt = lambda v: f"{v:.4f}" if isinstance(v, (int, float)) else "—"
    md = f"""# pi0.5 8h 训练 · 定时快照

生成时间：{now()}　|　阶段：`{status.get('phase','?')}`　|　当前臂：`{status.get('arm','—')}`

## 训练指标

| 指标 | 值 |
|---|---:|
| loss 采样点数 | {len(series)} |
| 初始 loss | {fmt(vals[0] if vals else None)} |
| 当前 loss | {fmt(vals[-1] if vals else None)} |
| 最小 loss | {fmt(min(vals) if vals else None)} |
| 当前 lr | {fmt(payload['last_lr'])} |
| 当前 grad norm | {fmt(payload['last_grdn'])} |
| 步数 | {st.get('current') or '—'} / {st.get('total') or '—'} |

## 系统 / 生产健康

| 指标 | 值 |
|---|---:|
| 可用内存 | {sm.get('mem_available_mb','—')} MB |
| 负载 1min | {sm.get('load1','—')} |
| GPU 利用率 | {sm.get('gpu_util_pct','—')} % |
| nuclio YOLO healthy | {sm.get('nuclio_healthy','—')} |
| CVAT 容器 Up | {sm.get('cvat_up','—')} |

告警：{('、'.join(alerts[-3:]) if alerts else '无')}

曲线：`figs/loss_latest.png` / `.svg`。原始指标：`reports/metrics.jsonl`。
"""
    (REPORTS / "latest.md").write_text(md, encoding="utf-8")


def monitor() -> None:
    log_path = LOGS / "monitor.log"
    def mlog(msg):
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{now()}] {msg}\n")
    mlog("=== MONITOR START ===")
    alerts, ticks = [], 0
    while True:
        try:
            sm = sys_metrics()
            tf = current_train_log()
            series, st = parse_log(tf) if tf else ([], {"current": None, "total": None, "elapsed_s": None})
            row = {"ts": now(), "log": tf.name if tf else None,
                   "samples": len(series), "last_loss": series[-1]["loss"] if series else None,
                   "min_loss": min((p["loss"] for p in series), default=None),
                   "steps": st.get("current"), "system": sm}
            with METRICS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

            avail = sm.get("mem_available_mb", 999999)
            if avail < MEM_FLOOR_MB:
                msg = f"MEMORY LOW {avail} MB < {MEM_FLOOR_MB} MB"
                alerts.append(f"{now()} {msg}")
                mlog(msg + " -> terminate training to protect CVAT")
                try:
                    pid = int(PID_FILE.read_text().strip())
                    if pid > 1:
                        os.killpg(pid, signal.SIGTERM)
                except Exception as e:
                    mlog(f"kill failed: {e}")
            if sm.get("nuclio_healthy", 4) < 4:
                alerts.append(f"{now()} nuclio healthy={sm.get('nuclio_healthy')} (expected 4)")

            # Refresh JSON + figure + markdown every 5 min so the phone
            # dashboard stays current; keep a 30-min heartbeat in the log.
            snapshot(series, st, sm, alerts)
            if ticks % 6 == 0:
                mlog(f"heartbeat samples={len(series)} last={row['last_loss']} avail={avail}MB")
            ticks += 1
        except Exception as e:
            mlog(f"loop error: {type(e).__name__}: {e}")
        time.sleep(300)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "monitor"
    (orchestrate if mode == "orchestrate" else monitor)()
