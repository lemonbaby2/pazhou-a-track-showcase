#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加/刷新 index.html 的第九、十章：
  九、Isaac Lab 环境覆盖矩阵（类别 / 环境名 / 状态）
  十、差距诊断与改进路线（鸭子为什么还不够稳）
幂等：已存在则整段替换。regen_ch8.py 只改第八章，不会碰这两章。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(BASE, "index.html")

OK = '<span class="pill ok">已出片</span>'
QUE = '<span class="pill warn">已入队</span>'
BAD = '<span class="pill bad">失败待查</span>'
SBK = '<span class="pill">备用</span>'

ROWS = [
    ("机械狗", "Isaac-Velocity-Flat-UnitreeGo2", OK + " E01", "平地速度跟踪 · 120 s"),
    ("机械狗", "Isaac-Velocity-Rough-UnitreeGo2", OK + " E02", "粗糙地形越障 · 120 s"),
    ("四足", "Isaac-Velocity-Rough-AnymalD", OK + " E03", "工业四足越障 · 120 s"),
    ("四足", "Isaac-Velocity-Flat-AnymalD", QUE, "阶段 6 新增"),
    ("人形", "Isaac-Velocity-Rough-H1", OK + " E04", "官方 DGX Spark 样例 · 120 s"),
    ("人形", "Isaac-Velocity-Flat-G1", OK + " E05", "平地行走 · 120 s"),
    ("人形", "Isaac-Velocity-Flat-H1", QUE, "阶段 6 新增"),
    ("人形", "Isaac-Velocity-Rough-G1", QUE, "阶段 6 新增"),
    ("双足", "Isaac-Velocity-Rough-Cassie", OK + " E08", "粗糙地形 · 120 s"),
    ("双足", "Isaac-Velocity-Flat-Cassie", QUE, "阶段 6 新增"),
    ("机械臂", "Isaac-Lift-Cable-Franka", QUE, "⚠️ 原写 Lift-Cube-Franka，该任务在 3.0 不存在，已更正并重新入队"),
    ("机械臂", "Isaac-Reach-Franka", QUE, "已训练完成（franka_reach.done）"),
    ("机械臂", "Isaac-Open-Drawer-Franka", BAD, "跑满 2 h 超时：OV texture cache 创建失败（omni.rtx），非任务名问题"),
    ("灵巧手", "Isaac-Reorient-Cube-Allegro", OK + " E07", "四指灵巧手转立方体 · 120 s"),
    ("灵巧手", "Isaac-Reorient-Cube-Shadow", QUE, "阶段 6 新增"),
    ("灵巧手", "Isaac-Lift-KukaAllegro-Camera", SBK, "带相机版本，显存/渲染开销大，暂不排"),
    ("经典", "Isaac-Ant", SBK, "环境已核实在清单内，可不占大显存快速出片"),
    ("经典", "Isaac-Humanoid", SBK, "同上"),
    ("经典", "Isaac-Ant-Direct", SBK, "--"),
    ("经典", "Isaac-Humanoid-Direct", SBK, "--"),
]

PARITY = [
    ("01 篮球平衡", "Mjlab-Basketball-MicroDuck", 1500, "1.19e-06"),
    ("02 走路 / 扰动", "Mjlab-Velocity-Flat-MicroDuck", 500, "3.58e-07"),
    ("03 高跷 25 cm", "Mjlab-Stilt-Flat-MicroDuck", 500, "5.96e-07"),
    ("04 摆动旋转", "Mjlab-SwingPump-MicroDuck", 500, "8.34e-07"),
    ("05 球平衡 FastSAC", "microduck-ball-balance", 900, "2.68e-07"),
    ("06 梯面攀爬", "Mjlab-FloorDeskBlind-MicroDuck", 32, "8.94e-07"),
    ("09 跨缝跳跃", "Mjlab-PlatformJump-MicroDuck", 200, "3.87e-06"),
]

DIAG = [
    ("走路摇晃、步态不稳",
     "① 播放层把 10 s 源片拉成 120 s（12× 慢放），动态被拉长，观感比实际更飘；"
     "② 站的 walking 视频与 02 扰动视频共用同一张 ONNX（<code>BEST_alpha_walking.onnx</code>，"
     "sha <code>e36332d3…</code>），没有为「稳定步态」单独训过策略。",
     "用官方配方（BAM 舵机模型 + 域随机化 + 61 维观测契约）在 GB10 上重训 "
     "<code>Mjlab-Velocity-Flat-MicroDuck</code>，4096 并发、seed 7；成片改回 1× 真实倍速。",
     '<span class="pill warn">重训进行中</span>'),
    ("06 爬楼梯不够优秀",
     "官方 <code>climber.onnx</code> + <code>getup.onnx</code> 双策略 handoff，episode 只有 30 s；"
     "场景参数是硬凑的（<code>nconmax=768 / njmax=3072 / contact maxmatch=400</code>，"
     "airborne_grace=120 步）。历史 bug：TerrainEntityCfg 缺失导致 <code>foot_on_floor</code> 恒为 False。",
     "把 episode 拉到 120 s 真实时长（现在 30 s 靠拼接/慢放），并做 handoff 接触阈值的敏感性扫描。",
     '<span class="pill bad">待办</span>'),
    ("01 篮球平衡不够优秀",
     "recurrent 策略、1500 步收尾；球不在观测里，只能靠躯干间接平衡，收敛本身慢。"
     "一致性 1.19e-06 说明导出链路没问题，短板在策略侧。",
     "把收尾步数从 1500 提到 6000（与 02 看齐），并补一段「扰动下重平衡」的对照录制。",
     '<span class="pill bad">待办</span>'),
    ("外部基线对比（凯源的鸭子）",
     "未拿到对方仓库地址 / 截图（<code>Clipboard_Screenshot.png</code> 在本机和工作区都没找到），"
     "暂时无法做同口径对比。",
     "提供仓库链接或截图后，按同一组指标（velocity error / slip velocity / fall rate / 120 s 连续行走存活率）对齐比较。",
     '<span class="pill bad">缺素材</span>'),
]


def build():
    rows = "\n".join(
        f"      <tr><td>{c}</td><td><code>{e}</code></td><td>{s}</td><td>{n}</td></tr>"
        for c, e, s, n in ROWS
    )
    parity = "\n".join(
        f"      <tr><td>{a}</td><td><code>{b}</code></td><td>{c}</td><td><b>{d}</b></td></tr>"
        for a, b, c, d in PARITY
    )
    diag = "\n".join(
        f'    <div class="vcard">\n'
        f'      <h3>{t} {pill}</h3>\n'
        f'      <div class="reason"><b>诊断：</b>{why}</div>\n'
        f'      <div class="reason"><b>动作：</b>{act}</div>\n'
        f'    </div>'
        for t, why, act, pill in DIAG
    )

    return f'''
<section>
  <h2>九、Isaac Lab 环境覆盖矩阵（DGX 闲余算力）</h2>
  <p>DGX 上 <code>list_envs.py</code> 实测可用环境 <b>45 个</b>（Isaac Lab 3.0，任务名无 <code>-v0</code> 后缀）。
  下表是本项目已覆盖 / 已排队 / 备用的 20 个，<b>状态以 DGX 侧 <code>state/done.list</code> 为准</b>，不是计划口径。</p>
  <table>
    <tr><th>类别</th><th>环境名</th><th>状态</th><th>备注</th></tr>
{rows}
  </table>
  <div class="note">两处口径更正：① 队列里原来的 <code>Isaac-Lift-Cube-Franka</code> 在 Isaac Lab 3.0
  <b>并不存在</b>（正确名 <code>Isaac-Lift-Cable-Franka</code>），导致该任务当场失败、成片是别的任务的片段；已更正并重置重跑。
  ② 经典控制 <code>Isaac-Ant / Isaac-Humanoid</code> 已核实存在于环境中，随时可以排进去，不必长期挂「备用」。</div>
</section>

<section>
  <h2>十、差距诊断与改进路线（鸭子为什么还不够稳）</h2>
  <p><b>先说结论：不是导出/部署链路的锅。</b>下表是各任务 ONNX 与真实观测的一致性校验，
  最大绝对误差全部落在 <code>1e-7 ~ 1e-6</code>，远低于 <code>atol=1e-4</code> ——
  "不够优秀"只可能来自<b>策略本身、场景参数、以及录像方式</b>这三层。</p>
  <table>
    <tr><th>任务</th><th>task_id</th><th>校验步数</th><th>max_abs_output_error</th></tr>
{parity}
  </table>
  <div class="note">播放层的坑（新发现）：<code>walking_gpu_latest.mp4</code> 源片只有 <b>10 s</b>、
  <code>ladder_gpu_latest.mp4</code> 与 <code>basketball_gpu_latest.mp4</code> 只有 <b>30 s</b>，
  站点上的 120 s 版本是把它们拉长/循环出来的（walking 相当于 <b>12× 慢放</b>）。
  慢放会把每一帧的抖动放大到肉眼可辨，<b>观感上的"摇晃"至少有一部分是这么来的</b>。</div>
  <div class="vgrid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px;margin-top:14px">
{diag}
  </div>
  <div class="note">已启动的改进：<code>microduck_rl</code>（官方训练仓库）在 DGX 上
  <code>uv sync</code> 装通，<code>warp-lang 1.12.0</code> 识别到 <code>cuda:0 = NVIDIA GB10 (122 GiB, sm_121)</code>；
  <code>Mjlab-Velocity-Flat-MicroDuck</code> 以 <b>4096 并发 / seed 7</b> 重训中，
  迭代 3.09 s、上限 50000 iter，检查点走 wandb offline。
  基线读数（iter 97）：<code>error_vel_xy 0.56</code> · <code>fell_over 1.5%</code> · <code>slip_velocity 0.054</code>。
  注意 <code>--video</code> 在 headless DGX 上会因无 OpenGL 上下文直接崩，录像要单走 EGL 通道。</div>
</section>
'''


def main():
    html = open(INDEX, encoding="utf-8").read()
    block = build().rstrip() + "\n"
    pat = re.compile(r'\n<section>\s*<h2>(?:九|十)、.*?(?=\n<footer|\n</div>)', re.S)
    if "九、Isaac Lab 环境覆盖矩阵" in html:
        # 替换已有的 九+十 两章
        pat2 = re.compile(r'\n<section>\s*<h2>九、Isaac Lab 环境覆盖矩阵.*?(?=\n<footer|\n</div>)', re.S)
        if not pat2.search(html):
            print("ERROR: 找到第九章标记但定位失败")
            return 2
        html = pat2.sub(block, html, count=1)
        mode = "替换"
    else:
        # 插在 footer 之前（footer 现在是整页最后一块，所有 section 都在 .wrap 内）
        footer = html.rfind("<footer")
        if footer > 0:
            anchor = footer
        else:
            anchor = html.rfind("</body>")
        html = html[:anchor] + block + "\n" + html[anchor:]
        mode = "追加"

    open(INDEX, "w", encoding="utf-8").write(html)
    print(f"第九/十章 已{mode}：section {html.count('<section')} / {html.count('</section>')}")
    print(f"video 总数: {html.count('<video')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
