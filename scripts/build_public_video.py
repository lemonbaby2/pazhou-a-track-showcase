"""Build a 3-minute narrated showcase video and a small web playback rendition."""
from __future__ import annotations

import json
import math
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUT = ROOT / "out" / "pazhou_video_voice_20261107"
ASSETS = SITE / "assets"
CHAPTER_SECONDS = 15
FPS = 10
W, H = 1280, 720
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD_PATH = Path(r"C:\Windows\Fonts\msyhbd.ttc")
BG, PANEL, INK, SUB, TEAL, GOLD, BLUE, LINE = "#0c1219", "#14212b", "#edf4f4", "#a9b8be", "#63e0c3", "#f0c979", "#9ec8ff", "#293b46"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD_PATH if bold else FONT_PATH), size)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, fill: str = INK, bold: bool = False) -> None:
    draw.text(xy, value, font=font(size, bold), fill=fill)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str = PANEL, outline: str = LINE, r: int = 18, width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def fit_image(path: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    im.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "#ffffff")
    canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return canvas


def wrap(text_value: str, max_chars: int = 25) -> list[str]:
    out = []
    for paragraph in text_value.split("\n"):
        while len(paragraph) > max_chars:
            out.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        if paragraph:
            out.append(paragraph)
    return out


def slide_base(chapter: dict, index: int, total: int) -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for y in range(H):
        mix = y / H
        c1, c2 = (12, 18, 25), (18, 36, 44)
        c = tuple(round(c1[k] * (1 - mix) + c2[k] * mix) for k in range(3))
        d.line((0, y, W, y), fill=c)
    text(d, (58, 42), "PAZHOU 2026  /  EMBODIED SERVICE", 16, TEAL, True)
    text(d, (58, 126), f"{index + 1:02d}", 70, TEAL, True)
    text(d, (58, 220), chapter["title"], 42, INK, True)
    d.line((60, 292, 620, 292), fill=TEAL, width=3)
    subtitle_lines = wrap(chapter["narration"], 26)
    yy = 323
    for line in subtitle_lines[:5]:
        text(d, (60, yy), line, 24, SUB)
        yy += 40
    rounded(d, (694, 112, 1220, 590), PANEL, "#31515b", 22)
    text(d, (726, 136), "本地复现 · 可审计结果", 19, GOLD, True)

    # Visuals tied to recorded artifacts and measured results.
    if index == 0:
        labels = ["夹托盘", "取两瓶", "端盘移动", "逐瓶上桌", "语音通知"]
        for j, label in enumerate(labels):
            x = 728 + (j % 2) * 224
            y = 188 + (j // 2) * 96
            rounded(d, (x, y, x + 202, y + 62), "#182c35", "#36535c", 13)
            text(d, (x + 16, y + 16), f"{j + 1:02d}  {label}", 21, TEAL, True)
        text(d, (728, 492), "规则来源：参赛者提供的 A 赛道任务 PDF", 15, SUB)
    elif index == 1:
        nodes = [(756, 227, "托盘"), (1007, 227, "两瓶水"), (1007, 419, "客人桌"), (756, 419, "语音")]
        for x, y, label in nodes:
            rounded(d, (x, y, x + 144, y + 72), "#19333b", TEAL, 16)
            text(d, (x + 28, y + 20), label, 22, INK, True)
        for points in [((900, 263), (1002, 263)), ((1079, 302), (1079, 413)), ((1002, 454), (906, 454))]:
            d.line((*points[0], *points[1]), fill=GOLD, width=5)
    elif index == 2:
        for j, (big, small) in enumerate([("90", "分钟总赛时"), ("5", "分钟 / 轮"), ("2", "最多轮数")]):
            x = 722 + j * 160
            rounded(d, (x, 244, x + 142, 412), "#1b2e37", "#35515b", 18)
            text(d, (x + 28, 265), big, 57, TEAL if j < 2 else GOLD, True)
            text(d, (x + 14, 350), small, 17, SUB)
        text(d, (727, 460), "附件没有完整评分表或官方验收器", 20, GOLD, True)
    elif index == 3:
        rows = [("任务层", "状态机 · 超时 · 恢复"), ("接口层", "动作适配 · 感知输入"), ("后端", "本地 2D mock 仿真")]
        for j, (left, right) in enumerate(rows):
            y = 212 + j * 98
            rounded(d, (728, y, 1180, y + 68), "#182c35", "#36535c", 14)
            text(d, (746, y + 18), left, 19, TEAL, True)
            text(d, (865, y + 18), right, 18, INK)
    elif index in (4, 5, 6):
        cards = {
            4: [("50", "episodes"), ("65k", "frames"), ("50Hz", "sampling"), ("3", "cameras")],
            5: [("50", "episodes"), ("55k", "frames"), ("50Hz", "sampling"), ("14D", "actions")],
            6: [("RoboMIND", "多机器人"), ("DROID", "Franka 单臂"), ("Open X", "混合数据集")],
        }[index]
        for j, (big, small) in enumerate(cards):
            x = 728 + (j % 2) * 222
            y = 202 + (j // 2) * 112
            rounded(d, (x, y, x + 200, y + 84), "#182c35", "#36535c", 13)
            text(d, (x + 14, y + 12), big, 27 if len(big) < 8 else 20, TEAL, True)
            text(d, (x + 14, y + 52), small, 16, SUB)
        text(d, (730, 450), "数据只作迁移参考，不匹配比赛平台动作空间", 15, GOLD)
    elif index == 7:
        checks = [("22 / 22", "文件哈希与字节数"), ("120k", "Parquet 记录行"), ("100", "episodes"), ("8 / 8", "视频采样解码")]
        for j, (big, label) in enumerate(checks):
            y = 192 + j * 81
            d.ellipse((740, y + 5, 770, y + 35), fill=TEAL)
            text(d, (790, y), big, 25, TEAL, True)
            text(d, (970, y + 5), label, 17, INK)
    elif index == 8:
        text(d, (736, 195), "RTX 5060 Ti · CUDA 12.8", 19, TEAL, True)
        for j, (label, value, width, color) in enumerate([("Train MSE", "0.00621", 130, TEAL), ("Held-out MSE", "0.00805", 169, BLUE)]):
            y = 278 + j * 110
            text(d, (736, y), label, 19, SUB)
            d.rounded_rectangle((736, y + 39, 1156, y + 76), 10, fill="#243944")
            d.rounded_rectangle((736, y + 39, 736 + width, y + 76), 10, fill=color)
            text(d, (736 + width + 12, y + 43), value, 18, INK, True)
        text(d, (736, 508), "10 epochs  ·  15.46 sec", 17, GOLD)
    elif index == 9:
        gif_path = ASSETS / "demo.gif"
        if gif_path.exists():
            gif = Image.open(gif_path)
            frames = [f.convert("RGB") for f in ImageSequence.Iterator(gif)]
            return im, frames
        for j, label in enumerate(["托盘行驶", "倾角 12.2°", "恢复 1 次", "交付 2 / 2"]):
            rounded(d, (728, 206 + j * 77, 1180, 262 + j * 77), "#19333b", TEAL, 12)
            text(d, (750, 221 + j * 77), label, 20, INK, True)
    elif index == 10:
        im.paste(fit_image(ASSETS / "timeline.png", (460, 255)), (727, 205))
        text(d, (738, 485), "pytest: 17 passed", 25, TEAL, True)
    elif index == 11:
        todo = ["等待官方评分细则", "接入比赛 SDK / 官方仿真器", "采集获准的真机任务数据", "恢复 DGX 与正式发布连接"]
        for j, item in enumerate(todo):
            y = 202 + j * 75
            rounded(d, (728, y, 1180, y + 54), "#182c35", "#36535c", 12)
            text(d, (747, y + 10), f"□  {item}", 18, INK)
    d.line((60, 640, 1220, 640), fill=LINE, width=2)
    text(d, (60, 656), "PAZHOU A-TRACK  ·  LOCAL MOCK + EXTERNAL DATA BASELINE", 13, SUB)
    return im


def prepare_audio(chapters: list[dict], tmp_dir: Path) -> Path:
    voice_dir = OUT
    audio_pieces: list[bytes] = []
    ref_params = None
    target_frames = None
    for idx in range(len(chapters)):
        source = voice_dir / f"chapter_{idx + 1:02d}.wav"
        with wave.open(str(source), "rb") as wav:
            params = wav.getparams()
            raw = wav.readframes(wav.getnframes())
        if ref_params is None:
            ref_params = params
            target_frames = CHAPTER_SECONDS * params.framerate
        elif (params.nchannels, params.sampwidth, params.framerate) != (ref_params.nchannels, ref_params.sampwidth, ref_params.framerate):
            raise RuntimeError("Narration WAV formats differ across chapters")
        nframes = len(raw) // (params.nchannels * params.sampwidth)
        assert target_frames is not None
        if nframes > target_frames:
            speed = min(1.48, nframes / target_frames)
            temp = tmp_dir / f"chapter_{idx + 1:02d}_fast.wav"
            subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(source), "-filter:a", f"atempo={speed:.4f}", "-ac", str(params.nchannels), "-ar", str(params.framerate), "-sample_fmt", "s16", str(temp)], check=True)
            with wave.open(str(temp), "rb") as wav:
                raw = wav.readframes(wav.getnframes())
            nframes = len(raw) // (params.nchannels * params.sampwidth)
        if nframes > target_frames:
            raw = raw[: target_frames * params.nchannels * params.sampwidth]
            nframes = target_frames
        silence = b"\0" * ((target_frames - nframes) * params.nchannels * params.sampwidth)
        audio_pieces.append(raw + silence)
    out = tmp_dir / "narration_3min.wav"
    assert ref_params is not None
    with wave.open(str(out), "wb") as wav:
        wav.setnchannels(ref_params.nchannels)
        wav.setsampwidth(ref_params.sampwidth)
        wav.setframerate(ref_params.framerate)
        wav.writeframes(b"".join(audio_pieces))
    return out


def main() -> None:
    chapters = json.loads((SITE / "video_chapters.json").read_text(encoding="utf-8"))
    if len(chapters) != 12:
        raise ValueError("Expected twelve 15-second chapters for a 3-minute video")
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    wav_path = prepare_audio(chapters, OUT)
    output = OUT / "pazhou_a_showcase_3min_720p.mp4"
    cmd = [FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0", "-i", str(wav_path), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "96k", "-t", "180", "-movflags", "+faststart", str(output)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    gif_frames = [f.convert("RGB") for f in ImageSequence.Iterator(Image.open(ASSETS / "demo.gif"))]
    base_slides = []
    for i, chapter in enumerate(chapters):
        rendered = slide_base(chapter, i, len(chapters))
        if isinstance(rendered, tuple):
            base, special_frames = rendered
            base_slides.append((base, special_frames))
        else:
            base_slides.append((rendered, None))
    for frame_no in range(180 * FPS):
        seconds = frame_no / FPS
        chapter_idx = min(11, int(seconds // CHAPTER_SECONDS))
        within = seconds - chapter_idx * CHAPTER_SECONDS
        base, special = base_slides[chapter_idx]
        frame = base.copy()
        if special:
            source = special[int(within * 10) % len(special)]
            source.thumbnail((464, 260), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (464, 260), "#fff")
            canvas.paste(source, ((464 - source.width) // 2, (260 - source.height) // 2))
            frame.paste(canvas, (725, 206))
            d = ImageDraw.Draw(frame)
            d.rounded_rectangle((720, 201, 1194, 471), radius=8, outline="#63e0c3", width=3)
            text(d, (738, 485), "2 / 2 瓶 · 一次倾斜恢复", 19, TEAL, True)
        d = ImageDraw.Draw(frame)
        d.rectangle((60, 636, 1220, 642), fill="#233741")
        prog = (chapter_idx + within / CHAPTER_SECONDS) / len(chapters)
        d.rectangle((60, 636, int(60 + 1160 * prog), 642), fill=TEAL)
        text(d, (1106, 656), f"{int(seconds // 60):02d}:{int(seconds % 60):02d} / 03:00", 14, SUB)
        proc.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
    proc.stdin.close()
    code = proc.wait()
    if code:
        raise subprocess.CalledProcessError(code, cmd)
    high_download = SITE / "downloads" / "pazhou_a_showcase_3min.mp4"
    high_download.parent.mkdir(parents=True, exist_ok=True)
    high_download.write_bytes(output.read_bytes())
    web_video = ASSETS / "pazhou_a_showcase_3min_web.mp4"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(output), "-vf", "scale=640:360:flags=lanczos", "-r", "12", "-c:v", "libx264", "-preset", "medium", "-b:v", "105k", "-maxrate", "115k", "-bufsize", "230k", "-c:a", "aac", "-b:a", "32k", "-movflags", "+faststart", str(web_video)], check=True)
    print(json.dumps({"duration_seconds": 180, "fps": FPS, "resolution": "1280x720", "narration": "Mandarin SAPI voice", "high_quality_mp4": str(high_download), "web_mp4": str(web_video), "web_mp4_bytes": web_video.stat().st_size}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
