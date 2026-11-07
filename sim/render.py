"""PIL 渲染：把仿真帧画成俯视图 + HUD，并输出 GIF / 关键帧 / 时间线。"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

W, H = 960, 620
MAP = (24, 70, 664, 590)      # left, top, right, bottom
HUD_X = 690

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]

COL_BG = (246, 248, 252)
COL_GRID = (228, 233, 242)
COL_INK = (32, 40, 56)
COL_MUTED = (120, 132, 152)
COL_ACCENT = (34, 108, 214)
COL_OK = (26, 148, 96)
COL_WARN = (214, 140, 30)
COL_ERR = (200, 60, 60)
COL_TRAY = (150, 160, 176)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


class Renderer:
    def __init__(self, cfg: dict):
        layout = cfg["layout"]
        self.cfg = cfg
        self.xmin, self.xmax = -0.5, 5.1
        self.ymin, self.ymax = -1.1, 3.1
        self.l, self.t, self.r, self.b = MAP
        self.tray_limit = float(cfg["tray"]["tilt_limit_deg"])
        self.f_title = load_font(22)
        self.f_big = load_font(26)
        self.f = load_font(15)
        self.f_small = load_font(13)
        self.layout = layout

    # world -> screen
    def sx(self, x: float) -> float:
        return self.l + (x - self.xmin) / (self.xmax - self.xmin) * (self.r - self.l)

    def sy(self, y: float) -> float:
        return self.b - (y - self.ymin) / (self.ymax - self.ymin) * (self.b - self.t)

    def render(self, frame: Dict) -> Image.Image:
        img = Image.new("RGB", (W, H), COL_BG)
        d = ImageDraw.Draw(img)
        self._grid(d)
        self._zones(d)
        self._bottles(d, frame)
        self._robot(d, frame)
        self._hud(d, frame)
        return img

    def _grid(self, d):
        for i in range(7):
            x = self.sx(i)
            d.line([(x, self.t), (x, self.b)], fill=COL_GRID)
        for j in range(5):
            y = self.sy(j - 1)
            d.line([(self.l, y), (self.r, y)], fill=COL_GRID)

    def _zones(self, d):
        # 服务待命区
        sx, sy = self.sx(self.layout["standby"]["x"]), self.sy(self.layout["standby"]["y"])
        d.ellipse([sx - 46, sy - 46, sx + 46, sy + 46], outline=COL_ACCENT, width=2)
        d.text((sx - 34, sy + 50), "服务待命区", font=self.f_small, fill=COL_MUTED)

        # 备餐台
        px, py = self.layout["prep"]["x"], self.layout["prep"]["y"]
        d.rounded_rectangle([self.sx(px) - 30, self.sy(py) - 52,
                             self.sx(px) + 30, self.sy(py) + 52],
                            radius=10, outline=COL_MUTED, width=2)
        d.text((self.sx(px) - 24, self.sy(py) - 76), "饮品备餐台", font=self.f_small, fill=COL_MUTED)

        # 客人桌
        gx, gy = self.layout["guest"]["x"], self.layout["guest"]["y"]
        d.rounded_rectangle([self.sx(gx) - 26, self.sy(gy) - 56,
                             self.sx(gx) + 26, self.sy(gy) + 56],
                            radius=10, outline=COL_MUTED, width=2)
        d.text((self.sx(gx) - 24, self.sy(gy) + 64), "客人用餐桌", font=self.f_small, fill=COL_MUTED)

        # 服务通道
        d.line([(self.sx(self.layout["standby"]["x"]), self.sy(self.layout["standby"]["y"])),
                (self.sx(px), self.sy(py)),
                (self.sx(gx), self.sy(gy))],
               fill=(210, 218, 232), width=3)

    def _bottles(self, d, frame):
        col = {"prep": (60, 130, 220), "tray": (26, 148, 96),
               "table": (214, 140, 30), "held": (26, 148, 96), "floor": COL_ERR}
        for bid, x, y, loc in frame["bottles"]:
            cx, cy = self.sx(x), self.sy(y)
            c = col.get(loc, COL_MUTED)
            d.rounded_rectangle([cx - 6, cy - 13, cx + 6, cy + 13], radius=4, fill=c)
            d.text((cx - 9, cy - 30), bid, font=self.f_small, fill=c)

    def _robot(self, d, frame):
        cx, cy = self.sx(frame["x"]), self.sy(frame["y"])
        import math
        yaw = frame["yaw"]
        hx, hy = cx + math.cos(yaw) * 26, cy - math.sin(yaw) * 26
        # 托盘（朝向前方）
        tx, ty = cx + math.cos(yaw) * 20, cy - math.sin(yaw) * 20
        d.rounded_rectangle([tx - 22, ty - 14, tx + 22, ty + 14], radius=5,
                            outline=COL_TRAY, width=3)
        # 车身
        d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=(255, 255, 255),
                  outline=COL_ACCENT, width=3)
        d.line([(cx, cy), (hx, hy)], fill=COL_ACCENT, width=4)

    def _hud(self, d, frame):
        x = HUD_X
        y = 74
        d.text((x, 24), "A 赛道 · 商业饮品服务", font=self.f_title, fill=COL_INK)
        d.text((x, y), "状态", font=self.f_small, fill=COL_MUTED)
        d.text((x, y + 18), frame["state"], font=self.f_big,
               fill=COL_OK if frame["state"] in ("DONE",) else
               (COL_ERR if frame["state"] == "ABORT" else COL_ACCENT))
        y += 58

        d.text((x, y), "模拟用时  %.1f s" % frame["t"], font=self.f, fill=COL_INK)
        d.text((x, y + 22), "托盘倾角  %.1f° / 限 %.0f°" % (abs(frame["tilt"]), self.tray_limit),
               font=self.f, fill=COL_ERR if abs(frame["tilt"]) > self.tray_limit else COL_INK)
        y += 54

        # 倾角条
        bw = 220
        d.rounded_rectangle([x, y, x + bw, y + 12], radius=6, fill=(232, 236, 244))
        frac = min(1.0, abs(frame["tilt"]) / max(1e-6, self.tray_limit))
        c = COL_OK if frac < 0.65 else (COL_WARN if frac < 1.0 else COL_ERR)
        if frac > 0:
            d.rounded_rectangle([x, y, x + bw * frac, y + 12], radius=6, fill=c)
        y += 26

        d.text((x, y), "托盘 %d 瓶   桌面 %d 瓶" % (frame["tray_count"], frame["table_count"]),
               font=self.f, fill=COL_INK)
        y += 34

        steps = [("① 启动服务", 0), ("② 备餐装盘", 1), ("③ 端盘配送", 2), ("④ 上饮通知", 3)]
        cur = self._phase(frame["state"])
        for label, idx in steps:
            if idx < cur:
                mark, c = "✓", COL_OK
            elif idx == cur:
                mark, c = "●", COL_ACCENT
            else:
                mark, c = "○", COL_MUTED
            d.text((x, y), "%s %s" % (mark, label), font=self.f, fill=c)
            y += 24

        d.text((x, 560), "仿真后端 · 无机器人也可跑通全流程", font=self.f_small, fill=COL_MUTED)

    @staticmethod
    def _phase(state: str) -> int:
        if state in ("BOOT", "ANNOUNCE", "NAV_PREP", "DETECT", "PICK_PLACE_1", "PICK_PLACE_2"):
            return 0 if state in ("BOOT", "ANNOUNCE") else 1
        if state in ("NAV_GUEST",):
            return 2
        if state in ("SERVE_1", "SERVE_2", "DONE"):
            return 3
        return 0


def save_gif(frames: List[Dict], cfg: dict, path: str, fps: int = 12, every: int = 2):
    r = Renderer(cfg)
    imgs = []
    for i, fr in enumerate(frames):
        if i % every:
            continue
        imgs.append(r.render(fr).resize((720, 465), Image.LANCZOS))
    if not imgs:
        return None
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    imgs[0].save(path, save_all=True, append_images=imgs[1:],
                 duration=int(1000 / max(1, fps)), loop=0, optimize=True)
    return path


def save_keyframes(frames: List[Dict], cfg: dict, path: str):
    r = Renderer(cfg)
    if not frames:
        return None
    picks = [0, len(frames) // 3, 2 * len(frames) // 3, len(frames) - 1]
    # 用「最大倾角帧」替换第三格，确保关键帧能展示托盘倾斜/恢复
    if frames:
        max_i = max(range(len(frames)), key=lambda i: abs(frames[i].get("tilt", 0.0)))
        picks[2] = max_i
    imgs = [r.render(frames[i]) for i in picks]
    sheet = Image.new("RGB", (W * 2, H * 2), "white")
    for k, im in enumerate(imgs):
        sheet.paste(im, ((k % 2) * W, (k // 2) * H))
    sheet = sheet.resize((W, H), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sheet.save(path)
    return path


def save_timeline(frames: List[Dict], path: str):
    if not frames:
        return None
    # 统计每个状态的起止时间
    spans: List[Tuple[str, float, float]] = []
    cur, t0 = frames[0]["state"], frames[0]["t"]
    for fr in frames[1:]:
        if fr["state"] != cur:
            spans.append((cur, t0, fr["t"]))
            cur, t0 = fr["state"], fr["t"]
    spans.append((cur, t0, frames[-1]["t"]))

    total = max(1e-6, frames[-1]["t"] - frames[0]["t"])
    lw, lh = 1080, 60 + 34 * len(spans)
    img = Image.new("RGB", (lw, lh), "white")
    d = ImageDraw.Draw(img)
    f = load_font(14)
    fs = load_font(12)
    d.text((24, 16), "任务状态时间线（仿真用时）", font=load_font(20), fill=COL_INK)
    x0, x1 = 220, lw - 40
    for i, (name, a, b) in enumerate(spans):
        y = 58 + i * 34
        d.text((24, y + 3), name, font=fs, fill=COL_INK)
        xa = x0 + (a - frames[0]["t"]) / total * (x1 - x0)
        xb = x0 + (b - frames[0]["t"]) / total * (x1 - x0)
        c = COL_OK if name == "DONE" else (COL_ERR if name == "ABORT" else COL_ACCENT)
        d.rounded_rectangle([xa, y, max(xa + 3, xb), y + 20], radius=5, fill=c)
        d.text((xb + 6, y + 3), "%.1fs" % (b - a), font=fs, fill=COL_MUTED)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path)
    return path
