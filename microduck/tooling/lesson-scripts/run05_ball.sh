#!/bin/bash
# 05 球平衡 FastSAC scratch smoke 训练 + ONNX 导出（standalone，无超时）
# 关键：cwd 必须在 MotrixLab 根目录（含 configs/），run_cli 才会注册
# --config-dir，task=<group> 语法才生效。
cd /home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab
export MUJOCO_GL=egl
export OMP_NUM_THREADS=4
export WANDB_MODE=disabled
export HOME=/home/nvidia

MOTRIX_PY=/home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab/.venv/bin/python
RUNNER=/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts/scripts/motrix_runner.py
TRAIN_SHIM=/home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab/scripts/train.py
EXPORT_SHIM=/home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab/scripts/export_onnx.py

echo "=== [1/2] FastSAC smoke train (scratch, 10 iters, 64 envs) ==="
"$MOTRIX_PY" "$RUNNER" train "$TRAIN_SHIM" \
  task=microduck-ball-balance/motrix.fastsac \
  num_envs=64 play=false render=false algo.asynchronous=false \
  algo.device=cuda algo.agent.compile=false algo.agent.amp=false \
  algo.agent.learning_starts=2 algo.agent.buffer_size=8 algo.agent.batch_size=64 \
  algo.agent.num_updates=1 algo.trainer.num_learning_iterations=10
TRAIN_RC=$?
echo "TRAIN_RC=$TRAIN_RC"
if [ $TRAIN_RC -ne 0 ]; then
  echo "BALL_FAILED"
  exit 1
fi

RUN_DIR=$(ls -td runs/*/ 2>/dev/null | head -1)
echo "RUN_DIR=$RUN_DIR"
if [ -z "$RUN_DIR" ]; then
  echo "NO_RUN_DIR"
  exit 1
fi

echo "=== [2/2] export ONNX (opset 11) ==="
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
