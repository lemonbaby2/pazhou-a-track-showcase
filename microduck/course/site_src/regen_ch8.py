#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重生成 index.html 第八章（具身智能 · DGX 闲余算力收割）。
扫描 videos/ 目录里的 isaac 产物，自动生成视频卡片。
以后 DGX 每跑完一个任务、拉回一个 mp4，跑一次本脚本即可。
"""
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
VIDEOS = os.path.join(BASE, "videos")
INDEX = os.path.join(BASE, "index.html")

# key -> (编号, 标题, 说明, 标签)
META = {
    "go2_flat":         ("E01", "Unitree Go2 · 平地", "四足机器狗 · 速度跟踪", "Isaac-Velocity-Flat-UnitreeGo2"),
    "go2_rough":        ("E02", "Unitree Go2 · 粗糙地形", "四足机器狗 · 越障行走", "Isaac-Velocity-Rough-UnitreeGo2"),
    "anymal_rough":     ("E03", "ANYmal D · 粗糙地形", "工业四足 · 越障行走", "Isaac-Velocity-Rough-AnymalD"),
    "h1_rough":         ("E04", "Unitree H1 · 人形", "人形机器人 · 粗糙地形", "Isaac-Velocity-Rough-H1"),
    "g1_flat":          ("E05", "Unitree G1 · 人形", "人形机器人 · 平地", "Isaac-Velocity-Flat-G1"),
    "franka_lift":      ("E06", "Franka · 抓取立方体", "七轴机械臂 · 操作任务", "Isaac-Lift-Cube-Franka"),
    "allegro_reorient": ("E07", "Allegro · 灵巧手", "四指灵巧手 · 立方体旋转", "Isaac-Reorient-Cube-Allegro"),
    "cassie_rough":     ("E08", "Cassie · 双足", "双足机器人 · 粗糙地形", "Isaac-Velocity-Rough-Cassie"),
}


def probe_duration(path):
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            stderr=subprocess.DEVNULL, timeout=25,
        ).decode().strip()
        return float(out)
    except Exception:
        return None


def human_size(n):
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}T"


def main():
    cards = []
    for key, (code, title, desc, env) in META.items():
        path = os.path.join(VIDEOS, key + ".mp4")
        if not os.path.isfile(path):
            continue
        dur = probe_duration(path)
        size = human_size(os.path.getsize(path))
        dur_txt = f"{dur:.0f}s" if dur else "—"
        cards.append(
            f'    <div class="vcard">\n'
            f'      <h3>{code} · {title}</h3>\n'
            f'      <div class="tag">Isaac Lab 3.0 · Newton(MJWarp) 物理 · {dur_txt} · {size}</div>\n'
            f'      <video controls preload="metadata" src="videos/{key}.mp4"></video>\n'
            f'      <div class="metrics">{desc} · <code>{env}</code></div>\n'
            f'    </div>'
        )

    if not cards:
        print("WARN: videos/ 里还没有任何 Isaac 产物，第八章保持原样")
        return 1

    block = (
        '\n<section>\n'
        '  <h2>八、具身智能 · DGX 闲余算力收割</h2>\n'
        '  <p>本站第三章是 MicroDuck 十项课程任务；本区块来自同一台 NVIDIA DGX Spark'
        '（GB10 · aarch64 · CUDA sm_121）的<strong>闲余算力</strong>：生产服务（SOP 推理 / CVAT）优先，'
        'GPU 空转时由 <code>embodied-harvest</code> 调度器自动领任务 —— Isaac Lab 3.0 训练 → '
        '推理录像 → 归一 120 秒 → 回传本站。物理后端为 Newton（MJWarp），非 PhysX。</p>\n'
        '  <div class="vgrid">\n'
        + "\n".join(cards)
        + '\n  </div>\n'
        '</section>\n'
    )

    html = open(INDEX, encoding="utf-8").read()
    pat = re.compile(r'\n<section>\s*<h2>八、具身智能 · DGX 闲余算力收割</h2>.*?</section>\n', re.S)
    if not pat.search(html):
        print("ERROR: 没找到第八章锚点")
        return 2
    html = pat.sub(block, html, count=1)
    open(INDEX, "w", encoding="utf-8").write(html)

    print(f"第八章已重生成：{len(cards)} 张卡片 -> {', '.join(c[0] for c in cards)}")
    print(f"section 配对: {html.count('<section')} / {html.count('</section>')}")
    print(f"video 总数: {html.count('<video')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
