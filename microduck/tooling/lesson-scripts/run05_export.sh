#!/bin/bash
# 05 导出（训练已完成，仅重跑导出；run_dir 取含 metadata.json 的最新叶子目录）
cd /home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab
export MUJOCO_GL=egl
export OMP_NUM_THREADS=4
export WANDB_MODE=disabled
export HOME=/home/nvidia

MOTRIX_PY=/home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab/.venv/bin/python
RUNNER=/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts/scripts/motrix_runner.py
EXPORT_SHIM=/home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab/scripts/export_onnx.py

RUN_DIR=$(dirname "$(find runs -name metadata.json 2>/dev/null | sort | tail -1)")
echo "RUN_DIR=$RUN_DIR"
if [ -z "$RUN_DIR" ] || [ "$RUN_DIR" = "." ]; then
  echo "NO_RUN_DIR"
  exit 1
fi
ls -la "$RUN_DIR/checkpoints/" 2>/dev/null | head -5

"$MOTRIX_PY" "$RUNNER" export "$EXPORT_SHIM" \
  run_dir="$RUN_DIR" \
  output=/home/nvidia/microduck-course-run/converted/motrix_ball_balance_restored.opset11.onnx \
  opset=11
EXPORT_RC=$?
echo "EXPORT_RC=$EXPORT_RC"
ls -la /home/nvidia/microduck-course-run/converted/motrix_ball_balance_restored.opset11.onnx 2>/dev/null
if [ $EXPORT_RC -ne 0 ]; then
  echo "BALL_FAILED"
  exit 1
fi
echo "BALL_DONE"
