#!/bin/bash
# 06 梯面 notebook 重跑（timeout 已 patch 到 3600s；climber/getup onnx 已就绪）
cd /home/nvidia/microduck-course-run
export PATH=/home/nvidia/.local/bin:$PATH
export HOME=/home/nvidia
export MICRODUCK_TOPIC_ROOT=/home/nvidia/microduck-course-run/topic
export MUJOCO_GL=egl
export MICRODUCK_DOWNLOAD_PROXY=
export http_proxy=
export https_proxy=
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
export WANDB_MODE=disabled
export MICRODUCK_RUN_BPU=0
export GIT_CONFIG_GLOBAL=/dev/null
export UV_HTTP_TIMEOUT=600
export HF_HUB_DISABLE_XET=1
export HF_HUB_OFFLINE=1
export MICRODUCK_POLICY_PYTHON=/home/nvidia/microduck-course-run/envs/lightnav/bin/python
export MICRODUCK_MODEL_ROOT=/home/nvidia/microduck-course-run
export MICRODUCK_OFFICIAL_ROOT=/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-official
export MICRODUCK_GPU_LADDER_CLIMBER=/home/nvidia/microduck-course-run/converted/official_ladder_climber.opset11.onnx
export MICRODUCK_GPU_LADDER_GETUP=/home/nvidia/microduck-course-run/converted/official_ladder_getup.opset11.onnx
export PYTHONPATH=/home/nvidia/.cache/uv/git-v0/checkouts/2baf9ba9fe47e195/62bd8ce:/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts/src:/home/nvidia/.cache/uv/archive-v0/1jB7y7ZPFtA6jJjq

setsid nohup /home/nvidia/microduck-course-run/envs/notebook/bin/python \
  /home/nvidia/microduck-course-run/run_notebook.py 06 \
  > /home/nvidia/microduck-course-run/06_notebook_rerun.log 2>&1 &
echo "LAUNCHED_06 pid=$!"
