#!/bin/bash
# 05 球平衡 notebook 重跑（资产已就绪：converted/motrix_ball_balance_restored.opset11.onnx）
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
export MOTRIX_ROOT=/home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab
export MOTRIX_PYTHON=/home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab/.venv/bin/python
export MICRODUCK_RUN_FASTSAC_SMOKE=1
export MICRODUCK_TRAIN_MODE=scratch

setsid nohup /home/nvidia/microduck-course-run/envs/notebook/bin/python \
  /home/nvidia/microduck-course-run/run_notebook.py 05 \
  > /home/nvidia/microduck-course-run/05_notebook_rerun.log 2>&1 &
echo "LAUNCHED_05 pid=$!"
