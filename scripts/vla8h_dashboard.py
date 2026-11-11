#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull the 8h VLA training snapshot from DGX and publish a mobile-friendly
GitHub Pages dashboard. Optionally prints a JSON digest for mail relays.

Usage:
  C:/Users/lzp/.workbuddy/binaries/python/versions/3.13.12/python.exe \
      C:/Users/lzp/duck-opt/push_report.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import paramiko

HOST, USER, PWD = "192.168.1.217", "nvidia", "nvidia"
REMOTE = "/home/nvidia/vla-8h"
REPO = Path("C:/Users/lzp/pazhou-showcase")
OUT = REPO / "site" / "vla-8h.html"
# Port 22 times out on this network; ssh.github.com:443 is reachable and
# authenticates with the same key. Keep 22 as a short-timeout fallback so the
# hourly automation never silently loses a dashboard update.
GH = "ssh://git@ssh.github.com:443/lemonbaby2/pazhou-a-track-showcase.git"
GH_FALLBACK = "git@github.com:lemonbaby2/pazhou-a-track-showcase.git"


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD, timeout=10)
    return c


def fetch(c, rel, default=""):
    try:
        s = c.open_sftp()
        data = s.open(REMOTE + "/" + rel).read().decode("utf-8", "replace")
        s.close()
        return data
    except Exception:
        return default


def jparse(txt, fallback=None):
    try:
        return json.loads(txt)
    except Exception:
        return fallback if fallback is not None else {}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def gpu_util(c):
    """DGX GB10 unified memory makes nvidia-smi emit '[N/A]' for memory
    fields; query utilization alone and read it here so the dashboard is
    correct without restarting the resident monitor process."""
    try:
        _, o, _ = c.exec_command(
            "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits",
            timeout=15)
        v = o.read().decode("utf-8", "replace").strip().splitlines()[0].split(",")[0].strip()
        return float(v)
    except Exception:
        return None


def main():
    c = connect()
    latest = jparse(fetch(c, "reports/latest.json"))
    status = jparse(fetch(c, "state/status.json"))
    svg = fetch(c, "figs/loss_latest.svg")
    protocol = fetch(c, "reports/PROTOCOL.md")
    final = fetch(c, "reports/FINAL.md")
    results = jparse(fetch(c, "state/results.json"), fallback=[])
    metrics_txt = fetch(c, "reports/metrics.jsonl")
    gpu = gpu_util(c)
    c.close()

    sm = latest.get("system", {}) or {}
    if gpu is not None:
        sm["gpu_util_pct"] = gpu
    phase = status.get("phase", latest.get("phase") or "—")
    arm = status.get("arm") or latest.get("arm") or "—"
    fmt = lambda v: f"{v:.4f}" if isinstance(v, (int, float)) else "—"

    # 8h wall-clock budget, from the orchestrator's recorded start time.
    started = status.get("started_at") or latest.get("generated_at")
    progress = "—"
    try:
        t0 = datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
        elapsed = max(0, int((datetime.now() - t0).total_seconds()))
        pct = min(100.0, elapsed / 28800 * 100)
        eta = (t0 + timedelta(hours=8)).strftime("%H:%M")
        progress = f"{elapsed // 60} min / 480 min · {pct:.1f}% · 预计 {eta}"
    except Exception:
        pass

    alert_n = len(latest.get("alerts", []) or [])
    cards = [
        ("当前 loss", fmt(latest.get("last_loss"))),
        ("最小 loss", fmt(latest.get("min_loss"))),
        ("loss 采样点", str(latest.get("samples", "—"))),
        ("步数", f"{latest.get('steps_current') or '—'} / {latest.get('steps_total') or '—'}"),
        ("学习率", fmt(latest.get("last_lr"))),
        ("grad norm", fmt(latest.get("last_grdn"))),
        ("GPU 利用率", f"{sm.get('gpu_util_pct', '—')} %"),
        ("可用内存", f"{sm.get('mem_available_mb', '—')} MB"),
        ("nuclio 健康", f"{sm.get('nuclio_healthy', '—')} / 4"),
        ("CVAT 容器 Up", str(sm.get("cvat_up", "—"))),
    ]
    card_html = "\n".join(
        f'<div class="card"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>'
        for k, v in cards
    )

    arms = [
        ("A_ki", "基线：Knowledge Insulation + QUANTILES", "π0.5 原生 flow matching"),
        ("B_lm", "解冻 VLM 语言模型", "Knowledge Insulation 消融"),
        ("C_mstd", "QUANTILES → MEAN_STD", "openpi LIBERO 参考配方"),
        ("D_beta", "Beta(1.5,1.0) → 均匀采样", "π0 论文 §4 timestep sampling"),
    ]
    done = {r.get("arm") for r in results} if isinstance(results, list) else set()
    arm_rows = "\n".join(
        f"<tr><td><code>{a}</code></td><td>{esc(b)}</td><td>{esc(d)}</td>"
        f"<td>{'✅ 已完成' if a in done else ('▶ 进行中' if a == arm else '待运行')}</td></tr>"
        for a, b, d in arms
    )

    recent_rows, recent_html = [], ""
    for line in [x for x in metrics_txt.splitlines() if x.strip()][-6:]:
        r = jparse(line)
        if not r:
            continue
        sysd = r.get("system", {}) or {}
        recent_rows.append(
            f"<tr><td><code>{esc(r.get('ts','—'))}</code></td>"
            f"<td>{fmt(r.get('last_loss'))}</td><td>{fmt(r.get('min_loss'))}</td>"
            f"<td>{esc(r.get('steps'))}</td>"
            f"<td>{esc(sysd.get('mem_available_mb','—'))} MB</td>"
            f"<td>{esc(sysd.get('nuclio_healthy','—'))} / 4</td></tr>")
    if recent_rows:
        recent_html = ("<section><h2>最近 6 次定时巡检</h2><table><thead><tr>"
                       "<th>时间</th><th>loss</th><th>最小 loss</th><th>步数</th>"
                       "<th>可用内存</th><th>nuclio</th></tr></thead><tbody>"
                       + "\n".join(recent_rows) + "</tbody></table></section>")

    protocol_html = ""
    if protocol.strip():
        protocol_html = (f'<section><h2>实验协议 · 论文方法复现边界</h2>'
                         f'<pre>{esc(protocol)}</pre></section>')
    final_html = ""
    if final.strip():
        final_html = f'<section><h2>最终结果</h2><pre>{esc(final)}</pre></section>'

    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>MicroDuck · π0.5 8h 训练实时看板</title>
<style>
:root{{color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:#0b1020;color:#e8ecf6;font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}
.wrap{{max-width:960px;margin:0 auto;padding:24px 18px 60px}}
h1{{font-size:24px;margin:0 0 6px}}
h2{{font-size:17px;margin:30px 0 12px;color:#9fb4ff}}
.sub{{color:#8a97b8;font-size:13px;margin-bottom:22px}}
.bar{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px}}
.pill{{background:#172145;border:1px solid #2c3a70;border-radius:999px;padding:5px 14px;font-size:13px}}
.pill b{{color:#7fe0b0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.card{{background:#131b36;border:1px solid #26325c;border-radius:12px;padding:14px}}
.k{{font-size:12px;color:#8a97b8;margin-bottom:6px}}
.v{{font-size:20px;font-weight:650;color:#e8ecf6;font-variant-numeric:tabular-nums}}
figure{{margin:0;background:#131b36;border:1px solid #26325c;border-radius:12px;padding:14px;overflow:auto}}
figure svg{{max-width:100%;height:auto;display:block}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:9px 10px;border-bottom:1px solid #26325c;text-align:left;vertical-align:top}}
th{{color:#8a97b8;font-weight:500}}
code{{background:#1b2547;padding:2px 6px;border-radius:5px;color:#9fd4ff}}
pre{{white-space:pre-wrap;background:#131b36;border:1px solid #26325c;border-radius:12px;padding:14px;font-size:12px;overflow:auto}}
.note{{background:#241c33;border-left:3px solid #b98cff;padding:12px 16px;border-radius:8px;color:#cbb9e8;font-size:13px}}
a{{color:#8fb4ff}}
footer{{margin-top:36px;color:#6f7c9e;font-size:12px}}
</style></head><body><div class="wrap">
<h1>MicroDuck · π0.5 8h 连续训练看板</h1>
<div class="sub">DGX Spark GB10 · 3.6B π0.5 · LIBERO v3.0 · DGX 每 5 分钟采集 · 整点自动同步 · 页面 5 分钟自动刷新</div>
<div class="bar">
  <span class="pill">阶段 <b>{esc(phase)}</b></span>
  <span class="pill">当前臂 <b>{esc(arm)}</b></span>
  <span class="pill">快照 <b>{esc(latest.get('generated_at', '—'))}</b></span>
  <span class="pill">8h 进度 <b>{esc(progress)}</b></span>
  <span class="pill">告警 <b>{alert_n}</b></span>
</div>
<div class="grid">{card_html}</div>
<h2>Loss 曲线</h2>
<figure>{svg if svg.strip().startswith('<svg') else '<p style="color:#8a97b8">曲线尚未生成（训练冒烟通过后每 5 分钟出图）</p>'}</figure>
<h2>自变量消融设计（论文方法复现）</h2>
<table><thead><tr><th>臂</th><th>自变量</th><th>对应方法</th><th>状态</th></tr></thead><tbody>{arm_rows}</tbody></table>
<div class="note"><b>边界声明：</b>8 小时只做少步数微调，<b>不复现论文榜单数值</b>。π0.5 论文第一阶段 FAST 预训练、
部署期高层子任务推理、60k steps × batch 384 全量配方、RoboTwin 评测均未复现（开源仓库缺代码 / aarch64 无 SAPIEN wheel / 算力差约 90×）。
loss / grad norm / lr 全部从训练日志正则解析，未插值、未伪造。</div>
{recent_html}
{protocol_html}
{final_html}
<footer>生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · 源数据 <code>/home/nvidia/vla-8h/reports/</code> ·
仓库 <a href="https://github.com/lemonbaby2/pazhou-a-track-showcase">pazhou-a-track-showcase</a></footer>
</div></body></html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")

    # Commit only if the page actually changed.
    def git(*args):
        env = dict(os.environ)
        env.setdefault("GIT_SSH_COMMAND", "ssh -o ConnectTimeout=10 -o BatchMode=yes")
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                              text=True, timeout=180, env=env)

    changed = git("status", "--porcelain", "site/vla-8h.html").stdout.strip()
    pushed = False
    if changed:
        git("add", "site/vla-8h.html")
        git("-c", "core.safecrlf=false", "commit", "-q", "-m",
            f"chore(vla-8h): sync training dashboard {datetime.now():%Y-%m-%d %H:%M}")
    # Push in both cases: a previous run may have committed successfully but
    # failed to push (e.g. port 22 timeout), leaving an unpushed dashboard.
    r = git("push", GH, "main")
    if r.returncode != 0:
        r = git("push", GH_FALLBACK, "main")
    pushed = (r.returncode == 0)

    digest = {
        "phase": phase, "arm": arm,
        "last_loss": latest.get("last_loss"), "min_loss": latest.get("min_loss"),
        "samples": latest.get("samples"), "steps": latest.get("steps_current"),
        "mem_available_mb": sm.get("mem_available_mb"),
        "nuclio_healthy": sm.get("nuclio_healthy"),
        "alerts": alert_n,
        "generated_at": latest.get("generated_at"),
        "pushed": pushed,
        "url": "https://lemonbaby2.github.io/pazhou-a-track-showcase/vla-8h.html",
    }
    print(json.dumps(digest, ensure_ascii=False))
    return digest


if __name__ == "__main__":
    main()
