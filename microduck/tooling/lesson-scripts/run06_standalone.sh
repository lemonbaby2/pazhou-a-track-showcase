#!/bin/bash
# 06 梯面 standalone GPU 录制：无 notebook 600s 超时限制
cd /home/nvidia/microduck-course-run
export MUJOCO_GL=egl
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
export WANDB_MODE=disabled
export PYTHONPATH=/home/nvidia/.cache/uv/git-v0/checkouts/2baf9ba9fe47e195/62bd8ce:/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts/src:/home/nvidia/.cache/uv/archive-v0/1jB7y7ZPFtA6jJjq
export MICRODUCK_VALIDATION_RUN_ID=06-standalone-ladder

mkdir -p topic/03-Notebook/outputs/gpu_videos
setsid nohup /home/nvidia/microduck-course-run/envs/lightnav/bin/python \
  topic/02-可运行代码/microduck-playground-stilts/scripts/bpu_official_ladder_pair_video.py \
  --backend gpu \
  --official-root /home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-official/experiments/desk-climb \
  --climber-onnx /home/nvidia/microduck-course-run/models/ladder/models/climber.onnx \
  --getup-onnx /home/nvidia/microduck-course-run/converted/official_ladder_getup.opset11.onnx \
  --output /home/nvidia/microduck-course-run/topic/03-Notebook/outputs/gpu_videos/ladder_gpu_latest.mp4 \
  --seconds 30 --physics-device cpu --num-envs 64 --record-env 17 \
  > /home/nvidia/microduck-course-run/ladder_standalone.log 2>&1 &
echo "LADDER_PID=$!"
