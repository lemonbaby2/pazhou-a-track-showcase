#!/usr/bin/env bash
# Three 48 s ladder segments (different seeds) concatenated to a 120 s reel.
set -u
R=/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts
M=/home/nvidia/microduck-course-run
OUT=$M/out120
PY=$R/.venv/bin/python
cd "$R" || exit 1
export MICRODUCK_NCONMAX=768 MICRODUCK_NJMAX=3072

i=0
for spec in "123:3" "456:5" "789:7"; do
  seed=${spec%%:*}; env=${spec##*:}
  i=$((i+1))
  echo "=== seg$i seed=$seed env=$env $(date +%H:%M:%S) ==="
  $PY scripts/bpu_official_ladder_pair_video.py --backend gpu \
    --official-root "$M/topic/02-可运行代码/microduck-playground-official/experiments/desk-climb" \
    --climber-onnx "$M/models/ladder/models/climber.onnx" \
    --getup-onnx "$M/converted/official_ladder_getup.opset11.onnx" \
    --output "$OUT/seg$i.mp4" --seconds 48 --physics-device cuda:0 \
    --num-envs 16 --record-env "$env" --seed "$seed" \
    --width 960 --height 720 >> "$OUT/seg$i.log" 2>&1
  echo "seg$i rc=$? $(ls -la $OUT/seg$i*.mp4 2>/dev/null | head -1)"
done

# concat whatever segments exist, then trim to 120 s
ls $OUT/seg*-step-0.mp4 2>/dev/null | sort > /tmp/seglist.txt
if [ -s /tmp/seglist.txt ]; then
  sed -i "s|^|file '|; s|$|'|" /tmp/seglist.txt
  ffmpeg -y -v error -f concat -safe 0 -i /tmp/seglist.txt -c copy -t 120 "$OUT/ladder_reel.mp4"
  ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/ladder_reel.mp4"
fi
echo "=== LADDER REEL DONE $(date +%H:%M:%S) ==="
