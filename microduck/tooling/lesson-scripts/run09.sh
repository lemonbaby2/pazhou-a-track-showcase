#!/bin/bash
# 09 跨缝跳跃 notebook 重跑（jump-home 资产已就绪）
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
export MICRODUCK_JUMP_HOME=/home/nvidia/microduck-course-run/jump-home

setsid nohup /home/nvidia/microduck-course-run/envs/notebook/bin/python \
  /home/nvidia/microduck-course-run/run_notebook.py 09 \
  > /home/nvidia/microduck-course-run/09_notebook_rerun.log 2>&1 &
echo "LAUNCHED_09 pid=$!"
