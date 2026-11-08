import re
from pathlib import Path

p = Path(
    r"C:\Users\lzp\Documents\xwechat_files\wxid_zmxb0wapngqm22_00d0\msg\file\2026-10\microduck-task2\datawhale_microduck\task3\index.html"
)
html = p.read_text(encoding="utf-8")

new_section = """<section>
  <h2>三、每任务 2 分钟 GPU 推理视频（9 段 · 120 秒）</h2>
  <p>全部由 DGX Spark（GB10 · aarch64 · sm_121）真实 MuJoCo/MJX 仿真 + ONNX 策略推理录制，每段 120 秒。
     <b>01–06</b> 为 1× 实时录制；<b>05/08/09</b> 原始单次 rollout 片段较短，采用多片段拼接后慢放至 120 秒
     （文件名含 <code>slow120</code>，非实时速度，便于逐帧观察）。</p>
  <div class="grid">
    <div class="vcard">
      <h3>01 · basketball 篮球平衡</h3>
      <div class="tag">120s · 1× 实时 · Mjlab-BallKick-Flat · 6000 steps · GPU 物理 + GPU 推理</div>
      <video controls preload="metadata" src="videos/basketball_gpu_latest.mp4"></video>
      <div class="metrics">一致性 <b>32/32 ✓</b> · max_abs <b>9.54e-07</b></div>
    </div>
    <div class="vcard">
      <h3>02 · walking 行走</h3>
      <div class="tag">120s · 1× 实时 · Mjlab-Velocity-Flat · 6000 steps</div>
      <video controls preload="metadata" src="videos/walking_gpu_latest.mp4"></video>
      <div class="metrics">命令 vx=<b>0.40 m/s</b> · 一致性 <b>32/32 ✓</b></div>
    </div>
    <div class="vcard">
      <h3>02 · perturbation 物理扰动</h3>
      <div class="tag">120s · 1× 实时 · 两次外力推动 · 6000 steps</div>
      <video controls preload="metadata" src="videos/perturbation_gpu_latest.mp4"></video>
      <div class="metrics">命令 vx=<b>0.28 m/s</b> · 推后恢复站立</div>
    </div>
    <div class="vcard">
      <h3>03 · stilt 高跷行走</h3>
      <div class="tag">120s · 1× 实时 · Mjlab-Stilt-Flat · 25cm 高跷</div>
      <video controls preload="metadata" src="videos/stilt_gpu_latest.mp4"></video>
      <div class="metrics">命令 vx=<b>0.16 m/s</b> · 一致性 <b>32/32 ✓</b></div>
    </div>
    <div class="vcard">
      <h3>04 · swing 摆动旋转</h3>
      <div class="tag">120s · 1× 实时 · Mjlab-SwingPump · 摆锤泵能</div>
      <video controls preload="metadata" src="videos/swing_gpu_latest.mp4"></video>
      <div class="metrics">一致性 <b>32/32 ✓</b> · max_abs <b>8.34e-07</b></div>
    </div>
    <div class="vcard">
      <h3>05 · ball_balance 球平衡</h3>
      <div class="tag">120s · 慢放（片段拼接）· FastSAC scratch smoke · 900 steps</div>
      <video controls preload="metadata" src="videos/ball_balance_slow120.mp4"></video>
      <div class="metrics">一致性 <b>32/32 ✓</b> · max_abs <b>2.68e-07</b></div>
    </div>
    <div class="vcard">
      <h3>06 · ladder 梯面攀爬</h3>
      <div class="tag">120s · 3 段不同种子拼接 · climber/getup 双策略 · 已修 terrain/airborne</div>
      <video controls preload="metadata" src="videos/ladder_120.mp4"></video>
      <div class="metrics">梯级 27 踏 · 桌面 0.66m · 手递手 <b>contact handoff ✓</b></div>
    </div>
    <div class="vcard">
      <h3>08 · LightNav0 视觉语言导航</h3>
      <div class="tag">120s · 慢放（三场景拼接）· apartment / living_room / corridor</div>
      <video controls preload="metadata" src="videos/lightnav_slow120.mp4"></video>
      <div class="metrics">三场景 <b>model_stop ×3</b> · 预测 37/42/47 次</div>
    </div>
    <div class="vcard">
      <h3>09 · long_jump 跨缝跳跃</h3>
      <div class="tag">120s · 慢放（预训练/续训/ONNX 三段拼接）</div>
      <video controls preload="metadata" src="videos/long_jump_slow120.mp4"></video>
      <div class="metrics">ONNX parity <b>6.6e-06</b> · 10 轮 PPO 精确恢复</div>
    </div>
  </div>
</section>"""

start = html.index("<section>\n  <h2>三、真实 GPU 推理视频回放")
end = html.index("<section>\n  <h2>四、各 Notebook 执行详情")
html = html[:start] + new_section + "\n\n" + html[end:]

# 文案同步：30 秒 → 120 秒
html = html.replace("climber/getup 双策略切换 30 秒 episode（CPU 物理 64 env + GPU 推理录制）",
                    "climber/getup 双策略 120 秒视频（terrain 实体 + airborne 判定已修）")
html = html.replace("climber/getup 双策略 30s 视频/json/trace", "climber/getup 双策略 120s 视频/json/trace")
html = html.replace("<td>30s episode</td>", "<td>120s episode</td>")

# 追加后端 API 章节
api = """
<section>
  <h2>七、后端 API（FastAPI + SQLite）</h2>
  <p>本站由 <code>app.py</code>（FastAPI）单端口服务托管：静态资源 + 只读 JSON API，启动时把
     <code>validation/*.json</code> 与 <code>videos/*.mp4</code> 汇总进 SQLite（<code>data/runs.db</code>）。</p>
  <table>
    <tr><th>方法</th><th>路径</th><th>说明</th></tr>
    <tr><td>GET</td><td><code>/api/health</code></td><td>存活与视频计数</td></tr>
    <tr><td>GET</td><td><code>/api/tasks</code></td><td>10 个任务 + 各自视频列表（含时长/大小）</td></tr>
    <tr><td>GET</td><td><code>/api/tasks/{id}</code></td><td>单任务详情（00–09）</td></tr>
    <tr><td>GET</td><td><code>/api/videos?min_seconds=120</code></td><td>视频索引，可按最短时长过滤</td></tr>
    <tr><td>GET</td><td><code>/api/summary</code></td><td>视频总数、≥120s 数量、验收 JSON 清单</td></tr>
  </table>
  <p>启动：<code>uvicorn app:app --host 0.0.0.0 --port $PORT</code></p>
</section>
"""
html = html.replace("</body>", api + "\n</body>")

p.write_text(html, encoding="utf-8")
print("index.html rewritten, bytes:", len(html))
print("120 秒 mention:", html.count("120s"), "| slow120:", html.count("slow120"))
