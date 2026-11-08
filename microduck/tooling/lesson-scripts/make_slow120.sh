#!/usr/bin/env bash
# Build 120 s reels for 05/08/09 from their real clips:
# concatenate the task's clips, then slow them to exactly 120 s (slow-motion).
set -u
V="C:/Users/lzp/Documents/xwechat_files/wxid_zmxb0wapngqm22_00d0/msg/file/2026-10/microduck-task2/datawhale_microduck/task3/videos"
T=/c/Users/lzp/microduck_task/reel
mkdir -p "$T"

build () { # out  speed  in1 [in2 ...]
  local out=$1 speed=$2; shift 2
  local list="$T/${out}_list.txt" ; : > "$list"
  for f in "$@"; do echo "file '$V/$f'" >> "$list"; done
  ffmpeg -y -v error -f concat -safe 0 -i "$list" -c copy "$T/${out}_cat.mp4" || return 1
  ffmpeg -y -v error -i "$T/${out}_cat.mp4" -filter:v "setpts=PTS*$speed" \
         -r 50 -t 120 -c:v libx264 -preset veryfast -crf 28 -pix_fmt yuv420p \
         -movflags +faststart -an "$V/${out}.mp4"
  local d; d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V/${out}.mp4" | cut -d. -f1)
  echo "$out  ${d}s  $(du -h "$V/${out}.mp4" | cut -f1)"
}

build "ball_balance_slow120" 6.7 "ball_balance_gpu_latest.mp4"
build "long_jump_slow120"    3.4 "long_jump_pretrained_latest.mp4" "long_jump_continued_latest.mp4" "long_jump_onnx_latest.mp4"
build "lightnav_slow120"     3.7 "lightnav_official_apartment_latest.mp4" "lightnav_living_room_latest.mp4" "lightnav_corridor_latest.mp4"
ls -la "$V" | tail -8
