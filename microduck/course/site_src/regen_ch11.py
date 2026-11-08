#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重生成 index.html 第十一章：MicroDuck 短跑实验室（PPO / MuJoCo Warp / 4096 并发）。

数据源（全部由 DGX 侧脚本产出，落到本站 duck/ 目录）：
  duck/sprint_metrics.json   ← DGX: export_sprint_metrics.py
  duck/sprint_speed.json     ← DGX: probe_sprint_speed.py（实测前进速度）
  duck/blog/*.mp4            ← 训练期录像快照（可归一 120 s）

用法：python regen_ch11.py
以后 DGX 每多一个 checkpoint / 曲线点，重跑本脚本即可。
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(BASE, "index.html")
DUCK = os.path.join(BASE, "duck")
VID = os.path.join(DUCK, "videos")

START = "<!-- CH11:START -->"
END = "<!-- CH11:END -->"

# 公开成绩（用户提供的口径）
PUBLIC = [("Hannes", 1.60, "#94a3b8"), ("Max Sumrall", 1.88, "#94a3b8"),
          ("电磁波Studio · 4090D", 2.07, "#f59e0b")]


def jload(name, default=None):
    p = os.path.join(DUCK, name)
    if not os.path.isfile(p):
        return default
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def probe_duration(path):
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            stderr=subprocess.DEVNULL, timeout=25).decode().strip()
        return float(out)
    except Exception:
        return None


def svg_chart(series, iters, width=980, height=210, colors=None, title=""):
    """极简多序列折线图（纯 SVG，不依赖外网 CDN）。"""
    if not series:
        return '<p class="reason">曲线数据尚未同步。</p>'
    colors = colors or ["#2563eb", "#1f9d55", "#c9821a", "#7c3aed"]
    pad_l, pad_r, pad_t, pad_b = 46, 12, 16, 26
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b
    n = max(len(iters), 2)
    x0, x1 = (iters[0], iters[-1]) if iters else (0, n - 1)
    span = max(x1 - x0, 1)

    # 统一归一（每条曲线各自 min-max，读趋势而非绝对值）
    parts = []
    legend = []
    for i, (name, vals) in enumerate(series.items()):
        if not vals:
            continue
        c = colors[i % len(colors)]
        lo, hi = min(vals), max(vals)
        rng = (hi - lo) or 1.0
        pts = []
        for k, v in enumerate(vals):
            it = iters[k] if k < len(iters) else k
            x = pad_l + (it - x0) / span * w
            y = pad_t + h - (v - lo) / rng * h
            pts.append(f"{x:.1f},{y:.1f}")
        parts.append(f'<polyline fill="none" stroke="{c}" stroke-width="2" points="{" ".join(pts)}"/>')
        legend.append(
            f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:14px;font-size:12px">'
            f'<i style="width:14px;height:3px;background:{c};display:inline-block;border-radius:2px"></i>'
            f'{html.escape(name)} <b style="color:#1f2933">{vals[-1]:.4g}</b></span>')
    axis = (
        f'<line x1="{pad_l}" y1="{pad_t + h}" x2="{pad_l + w}" y2="{pad_t + h}" stroke="#e3e8ef"/>'
        f'<text x="{pad_l}" y="{height - 8}" font-size="11" fill="#5b6b7b">iter {x0}</text>'
        f'<text x="{pad_l + w}" y="{height - 8}" font-size="11" fill="#5b6b7b" text-anchor="end">iter {x1}</text>'
    )
    return (f'<div style="margin:6px 0 2px">{title}</div>'
            f'<svg viewBox="0 0 {width} {height}" style="width:100%;height:auto;background:#fbfdff;'
            f'border:1px solid #e3e8ef;border-radius:10px">{"".join(parts)}{axis}</svg>'
            f'<div style="margin-top:6px">{"".join(legend)}</div>'
            f'<div class="metrics">纵轴为各指标自身 min–max 归一（只看形状，数值见右侧末值）。</div>')


def main() -> int:
    metrics = jload("sprint_metrics.json", {}) or {}
    speed = jload("sprint_speed.json", {}) or {}

    iters = metrics.get("iters") or []
    ser = metrics.get("series") or {}

    chart_series = {}
    if ser.get("error_vel_xy"):
        chart_series["速度误差 error_vel_xy"] = ser["error_vel_xy"]
    if ser.get("air_time_mean"):
        chart_series["腾空时间 air_time (s)"] = ser["air_time_mean"]
    if ser.get("mean_reward"):
        chart_series["回合奖励 mean_reward"] = ser["mean_reward"]

    chart = svg_chart(chart_series, iters, title="")

    # ---- 关键数字 ----
    peak = speed.get("forward_speed_peak_frame_mps")
    mean = speed.get("forward_speed_mean_mps")
    p95 = speed.get("forward_speed_p95_mps")
    ckpt = speed.get("checkpoint", "—")
    it_done = max(iters) if iters else 0
    last_err = (ser.get("error_vel_xy") or [None])[-1]
    last_air = (ser.get("air_time_mean") or [None])[-1]

    def fmt(v, unit="", nd=2):
        return "—" if v is None else f"{v:.{nd}f}{unit}"

    stats = f'''
  <div class="summary-big">
    <div class="stat"><div class="n">{fmt(peak) if peak else "训练中"}</div><div class="l">实测峰值前进速度 (m/s)</div></div>
    <div class="stat"><div class="n">{fmt(mean) if mean else "训练中"}</div><div class="l">平均前进速度 (m/s)</div></div>
    <div class="stat"><div class="n">{fmt(p95) if p95 else "训练中"}</div><div class="l">P95 前进速度 (m/s)</div></div>
    <div class="stat"><div class="n">{it_done}</div><div class="l">已完成迭代</div></div>
    <div class="stat"><div class="n">{fmt(last_air, "", 3)}</div><div class="l">腾空时间 (s)</div></div>
  </div>
  <div class="note">测速口径：<code>probe_sprint_speed.py</code> 在 CUDA 上并行 64 个环境、把前进命令<b>锁死</b>到
  <code>{speed.get("cmd_mps", 2.6)} m/s</code>，读 <code>root_link_lin_vel_b[:,0]</code>，
  丢掉前 {speed.get("warmup", 100)} 步暖机，统计剩余 {speed.get("steps", "—")} 步。
  检查点：<code>{html.escape(str(ckpt))}</code>。</div>'''

    # ---- 公开成绩对比条 ----
    rows = []
    for name, v, c in PUBLIC:
        rows.append((name, v, c))
    if peak:
        rows.append(("本机 DGX Spark（GB10）", float(peak), "#2563eb"))
    mx = max(r[1] for r in rows) * 1.12
    bars = "".join(
        f'<div style="display:flex;align-items:center;gap:10px;margin:5px 0">'
        f'<span style="width:190px;font-size:13px">{html.escape(n)}</span>'
        f'<span style="flex:1;background:#eef2f7;border-radius:6px;height:18px;position:relative">'
        f'<span style="display:block;width:{v / mx * 100:.1f}%;height:100%;background:{c};border-radius:6px"></span></span>'
        f'<b style="width:62px;text-align:right;font-size:13px">{v:.2f} m/s</b></div>'
        for n, v, c in rows)

    # ---- 视频卡片 ----
    cards = []
    if os.path.isdir(VID):
        for f in sorted(os.listdir(VID)):
            if not f.endswith(".mp4"):
                continue
            p = os.path.join(VID, f)
            dur = probe_duration(p)
            size = os.path.getsize(p) / 1024 / 1024
            m = re.search(r"step-(\d+)", f)
            step = m.group(1) if m else "?"
            cards.append(
                f'    <div class="vcard">\n'
                f'      <h3>训练快照 · step {step}</h3>\n'
                f'      <div class="tag">MuJoCo Warp 渲染 · {dur:.1f}s · {size:.1f} MB</div>\n'
                f'      <video controls preload="metadata" src="duck/videos/{f}"></video>\n'
                f'    </div>')
    video_block = ('  <div class="grid">\n' + "\n".join(cards) + '\n  </div>') if cards \
        else '<p class="reason">录像尚未同步（DGX 侧每 250 迭代出一段）。</p>'

    block = f'''{START}
<section>
  <h2>十一、MicroDuck 短跑实验室 · 4096 只鸭子挤一台 GB10</h2>
  <p><b>先说结论：</b>官方 <code>microduck_rl</code> 出厂配方只让鸭子跑 <b>0.4 m/s</b> ——
  <code>Mjlab-Velocity-Flat-MicroDuck</code> 的速度命令范围写死为 <code>lin_vel_x ∈ (-0.4, 0.4)</code>，
  那是"走路"。想把鸭子练成短跑选手（对标公开成绩 2.07 m/s），必须改三件事：
  <b>命令范围</b>、<b>奖励配方</b>、<b>回合长度</b>。本区块是这套改法在 DGX Spark 上的真实跑批。</p>
{stats}
  <h3 style="font-size:15px;margin-top:18px">公开成绩对标</h3>
  {bars}
  <div class="note">公开成绩为外部口径（1.6 / 1.88 / 2.07 m/s）。本机数字由上面的
  <code>probe_sprint_speed.py</code> 实测，不是训练日志里的 reward 换算。</div>

  <h3 style="font-size:15px;margin-top:18px">训练曲线（每 {max(1, (iters[1] - iters[0]) if len(iters) > 1 else 1)} 迭代一点）</h3>
  {chart}

  <h3 style="font-size:15px;margin-top:18px">冲刺配方 vs 官方配方</h3>
  <table>
    <tr><th>项目</th><th>官方 Velocity（走路）</th><th>本机 Sprint（短跑）</th><th>为什么这么改</th></tr>
    <tr><td>前进速度命令</td><td><code>(-0.4, 0.4)</code> m/s</td><td><code>(0.8, 2.6)</code> m/s</td><td>命令上不去，策略永远学不到高速；下界 0.8 保证全程都在跑</td></tr>
    <tr><td>横向 / 转向命令</td><td>±0.3 / ±1.0</td><td>±0.12 / ±0.25</td><td>收窄 ≈ "跑偏扣分"：只允许微调，不允许横着走</td></tr>
    <tr><td>朝向</td><td><code>rel_heading_envs=0</code></td><td><code>1.0</code>，heading ±0.12</td><td>全部环境按相对朝向采样，直道冲刺</td></tr>
    <tr><td>腾空奖励 <code>air_time</code></td><td>权重 3.0，窗口 [0.125, 0.300] s</td><td>权重 <b>5.0</b>，窗口 [0.10, 0.35] s</td><td>双击腾空是短跑的核心，窗口放宽让"腾得久"也被奖励</td></tr>
    <tr><td>速度追踪</td><td>2.0</td><td><b>3.0</b></td><td>主目标权重最高</td></tr>
    <tr><td>动作变形 <code>action_rate_l2</code></td><td>−0.1</td><td>−0.05</td><td>放宽，否则爆发力被罚死</td></tr>
    <tr><td>打滑 <code>foot_slip</code></td><td>−0.1</td><td><b>−0.35</b></td><td>加重 —— 滑步刷出来的是假速度</td></tr>
    <tr><td>头部姿态追踪</td><td>2.0</td><td>0.3</td><td>短跑不关心脖子，把容量让给腿</td></tr>
    <tr><td>回合长度</td><td>20 s</td><td>12 s</td><td>冲刺是高频片段，长回合稀释梯度</td></tr>
  </table>
  <div class="note">代码位置：<code>src/mjlab_microduck/tasks/microduck_sprint_env_cfg.py</code>（新增文件，
  不改官方任何一行），注册为独立任务 <code>Mjlab-Sprint-Flat-MicroDuck</code>，与官方任务并存。</div>

  <h3 style="font-size:15px;margin-top:18px">跑批参数</h3>
  <table>
    <tr><th>项</th><th>值</th><th>说明</th></tr>
    <tr><td>物理引擎</td><td>MuJoCo Warp（<code>warp-lang 1.12.0</code> + <code>mujoco-warp</code>）</td><td>4096 个环境在卡内并行，一次 kernel 推进</td></tr>
    <tr><td>算法</td><td>PPO（rsl_rl）</td><td>actor/critic 各 3×128 ELU</td></tr>
    <tr><td>并发环境</td><td>4096</td><td>GB10 统一内存 121 GB，鸭子仅 15 自由度，远未吃满</td></tr>
    <tr><td>迭代预算</td><td>5000</td><td>每 250 迭代存 checkpoint + 录一段视频</td></tr>
    <tr><td>控制频率</td><td>50 Hz</td><td>与 RK3566 实机 robotd 对齐</td></tr>
    <tr><td>训练卡</td><td>NVIDIA GB10（DGX Spark，sm_121）</td><td>与生产 SOP 推理共用，闲余算力跑</td></tr>
  </table>

  <h3 style="font-size:15px;margin-top:18px">算法与技能动物园 —— 这只鸭子还能怎么练</h3>
  <p>先说清一件事：官方训练栈 <code>microduck_rl</code> 的算法层来自 <b>rsl_rl</b>，
  而 rsl_rl 里<b>只有 PPO 和 distillation</b>（<code>rsl_rl/algorithms/</code> 下就这两个文件）。
  所以"换算法"不是改一行参数的事，得分清哪些是现成的、哪些要自己接。</p>
  <table>
    <tr><th>玩法</th><th>落地方式</th><th>能拿到什么</th><th>状态</th></tr>
    <tr><td><b>PPO 冲刺配方</b></td><td><code>Mjlab-Sprint-Flat-MicroDuck</code>（本次新增）</td><td>高速直道短跑，冲 2 m/s 量级</td><td><span class="pill ok">进行中</span></td></tr>
    <tr><td><b>PPO + RNN（LSTM/GRU）</b></td><td><code>--agent.actor.rnn-type lstm</code> + <code>--agent.actor.class-name RNNModel</code></td><td>带记忆的策略：扛观测延迟、扛遮挡、实机更稳</td><td><span class="pill warn">一条命令可跑</span></td></tr>
    <tr><td><b>PPO + 对称性增强</b></td><td>官方 <code>tasks/symmetry.py</code> + <code>--agent.algorithm.symmetry-cfg</code></td><td>左右对称数据增广，收敛更快、步态更规整</td><td><span class="pill warn">一条命令可跑</span></td></tr>
    <tr><td><b>Teacher-Student 蒸馏</b></td><td><code>rsl_rl/algorithms/distillation.py</code></td><td>teacher 吃特权信息（真实摩擦/速度），student 只看本体感知 → 可上实机</td><td><span class="pill warn">需写 runner</span></td></tr>
    <tr><td><b>域随机化强度扫描</b></td><td>BAM 舵机摩擦 / 齿轮间隙 / 控制延迟 / 电池电压</td><td>sim2real 稳定性，直接决定上真鸭子会不会摔</td><td><span class="pill warn">改配置即可</span></td></tr>
    <tr><td><b>粗糙地形课程</b></td><td><code>Mjlab-Velocity-Rough-MicroDuck</code> / <code>-Backlash-</code></td><td>台阶、斜坡、缝隙；抗扰能力</td><td><span class="pill">排队</span></td></tr>
    <tr><td><b>七个现成技能</b></td><td><code>Roulade</code>（前滚翻）<code>BallKick</code>（踢球）<code>Rollers</code>（轮滑）<code>StandUp</code> <code>SitStand</code> <code>GroundPick</code> <code>Spin</code> <code>Swizzle</code></td><td>一只鸭子八种动作，全部是注册好的任务，直接 <code>train &lt;task&gt;</code></td><td><span class="pill">待跑</span></td></tr>
    <tr><td>SAC / FastSAC</td><td>需自己写 env 适配（rsl_rl 不含 off-policy）</td><td>样本效率高，但这里 4096 并发下 PPO 更划算</td><td><span class="pill bad">不建议先做</span></td></tr>
    <tr><td>AMP（对抗运动先验）</td><td>需自写判别器 + 参考动作数据</td><td>学"像鸭子的跑"，不是"最快的跑"</td><td><span class="pill bad">缺参考动作数据</span></td></tr>
  </table>
  <div class="note">一句话取舍：<b>想让鸭子快 → 改命令范围 + 改奖励（本次做的事）；想让鸭子像鸭子 → AMP；想上真机不摔 → 域随机化 + RNN。</b>
  换 SAC/AMP 的收益在这台机器上不如先把 PPO 的命令空间和奖励配方调对。</div>

  <h3 style="font-size:15px;margin-top:18px">训练实拍（MuJoCo Warp 渲染）</h3>
{video_block}
</section>
{END}'''

    html_txt = open(INDEX, encoding="utf-8").read()
    if START in html_txt and END in html_txt:
        html_txt = re.sub(re.escape(START) + r".*?" + re.escape(END), block, html_txt, count=1, flags=re.S)
    else:
        anchor = "<footer>"
        if anchor not in html_txt:
            print("ERROR: 找不到插入锚点 <footer>")
            return 2
        html_txt = html_txt.replace(anchor, block + "\n\n" + anchor, 1)
    open(INDEX, "w", encoding="utf-8").write(html_txt)

    print(f"第十一章已生成：peak={fmt(peak)} mean={fmt(mean)} iters={it_done} videos={len(cards)}")
    print(f"section 配对: {html_txt.count('<section')} / {html_txt.count('</section>')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
