#!/usr/bin/env bash
# Fetch the 120 s renders from DGX, normalise names, compress for web.
set -u
DGX=nvidia@192.168.1.217
SRC=/home/nvidia/microduck-course-run/out120
TMP=/c/Users/lzp/microduck_task/v120
OUT="/c/Users/lzp/Documents/xwechat_files/wxid_zmxb0wapngqm22_00d0/msg/file/2026-10/microduck-task2/datawhale_microduck/task3/videos"
mkdir -p "$TMP"

fetch () { # remote_name local_name
  local r=$1 l=$2
  if [ -f "$TMP/$l.raw" ]; then echo "skip $l (cached)"; return 0; fi
  MSYS_NO_PATHCONV=1 scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
     "$DGX://$SRC/$r" "$TMP/$l.raw" 2>/dev/null || { echo "MISS $r"; return 1; }
  echo "got $l $(du -h "$TMP/$l.raw" | cut -f1)"
}

fetch basketball      basketball
fetch walking         walking
fetch perturbation    perturbation
fetch stilt           stilt
fetch swing           swing
fetch ladder.mp4      ladder

# compress + rename into the site
for f in basketball walking perturbation stilt swing ladder; do
  src="$TMP/$f.raw"
  [ -f "$src" ] || { echo "no $f"; continue; }
  dst="$OUT/${f}_gpu_latest.mp4"
  ffmpeg -y -v error -i "$src" -c:v libx264 -preset veryfast -crf 28 \
         -pix_fmt yuv420p -movflags +faststart -an "$dst" || { echo "ffmpeg fail $f"; continue; }
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$dst" | cut -d. -f1)
  echo "$f -> $(basename "$dst")  ${d}s  $(du -h "$dst" | cut -f1)"
done
ls -la "$OUT" | tail -15
