from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class LocalRefs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs: list[str] = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href", "src") and value:
                self.refs.append(value)


parser = LocalRefs()
parser.feed((SITE / "index.html").read_text(encoding="utf-8"))
missing = []
for ref in parser.refs:
    if ref.startswith(("http:", "https:", "#", "mailto:", "data:")):
        continue
    path = SITE / ref.split("#", 1)[0]
    if not path.exists():
        missing.append(ref)
if missing:
    raise SystemExit(f"Missing local page references: {missing}")

video = SITE / "downloads" / "pazhou_a_showcase_3min.mp4"
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
probe = subprocess.run([ffmpeg, "-i", str(video)], capture_output=True, text=True, encoding="utf-8", errors="replace")
metadata = probe.stderr
match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", metadata)
if not match:
    raise SystemExit("Could not read MP4 duration")
duration = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
if abs(duration - 180) > 0.1:
    raise SystemExit(f"Expected 180 s video; found {duration}")
if "Video:" not in metadata or "Audio:" not in metadata:
    raise SystemExit("MP4 must contain both video and narration audio")

files = [p for p in SITE.rglob("*") if p.is_file()]
too_large = [(str(p.relative_to(SITE)), p.stat().st_size) for p in files if p.stat().st_size > 5 * 1024 * 1024]
print({"local_references": len(parser.refs), "missing_references": missing,
       "mp4_duration_seconds": duration, "has_video": "Video:" in metadata,
       "has_audio": "Audio:" in metadata, "site_file_count": len(files),
       "site_total_bytes": sum(p.stat().st_size for p in files),
       "files_over_temporary_worker_5MiB_asset_limit": too_large})
if too_large:
    raise SystemExit("One or more assets exceed the temporary Workers static asset limit")
