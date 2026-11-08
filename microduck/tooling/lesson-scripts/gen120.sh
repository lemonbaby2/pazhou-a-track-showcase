#!/usr/bin/env bash
# Regenerate every task video at 120 s with GPU physics.
set -u
R=/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts
M=/home/nvidia/microduck-course-run
OUT=$M/out120
PY=$R/.venv/bin/python
mkdir -p "$OUT"
cd "$R" || exit 1
export MICRODUCK_NCONMAX=768 MICRODUCK_NJMAX=3072

run_gpu_inloop () {
  local task=$1 onnx=$2
  echo "=== [$(date +%H:%M:%S)] $task ==="
  $PY scripts/gpu_inloop_video.py --task "$task" --onnx "$onnx" \
      --output "$OUT/$task" --steps 6000 --physics-device cuda:0 \
      --policy-device cuda --width 960 --height 720 >> "$OUT/$task.log" 2>&1
  echo "[$(date +%H:%M:%S)] $task rc=$? files:"; ls -la "$OUT" | grep -i "$task" | head -3
}

run_ladder () {
  echo "=== [$(date +%H:%M:%S)] ladder ==="
  $PY scripts/bpu_official_ladder_pair_video.py --backend gpu \
      --official-root "$M/topic/02-可运行代码/microduck-playground-official/experiments/desk-climb" \
      --climber-onnx "$M/models/ladder/models/climber.onnx" \
      --getup-onnx "$M/converted/official_ladder_getup.opset11.onnx" \
      --output "$OUT/ladder.mp4" --seconds 120 --physics-device cuda:0 \
      --num-envs 16 --record-env 3 --width 960 --height 720 >> "$OUT/ladder.log" 2>&1
  echo "[$(date +%H:%M:%S)] ladder rc=$?"; ls -la "$OUT"/ladder.mp4 2>/dev/null
}

run_gpu_inloop basketball "$M/converted/basketball.opset11.onnx"
run_gpu_inloop walking    "$M/converted/walking.opset11.onnx"
run_gpu_inloop perturbation "$M/converted/walking.opset11.onnx"
run_gpu_inloop stilt      "$M/converted/stilts25.opset11.onnx"
run_gpu_inloop swing      "$M/converted/swing.opset11.onnx"
run_ladder

echo "=== ALL DONE $(date +%H:%M:%S) ==="
ls -la "$OUT"/*.mp4 2>/dev/null
