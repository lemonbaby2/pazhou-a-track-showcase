#!/bin/bash
# 08 LightNav notebook 重跑（lightnav-0 torch cu128 已修复）
cd /home/nvidia/microduck-course-run
export PATH=/home/nvidia/.local/bin:$PATH
export HOME=/home/nvidia
export MICRODUCK_TOPIC_ROOT=/home/nvidia/microduck-course-run/topic
export MUJOCO_GL=egl
export MICRODUCK_DOWNLOAD_PROXY=
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
export WANDB_MODE=disabled
export MICRODUCK_RUN_BPU=0
export GIT_CONFIG_GLOBAL=/dev/null
export UV_HTTP_TIMEOUT=600
export HF_HUB_DISABLE_XET=1
export HF_HUB_OFFLINE=1
export LIGHTNAV_ROOT=/home/nvidia/LightNav-0
export LIGHTNAV_MODEL_ENV=/home/nvidia/microduck-course-run/envs/lightnav-0
export LIGHTNAV_MODEL_PATH=/home/nvidia/microduck-course-run/checkpoints/LightNav-0
export LIGHTNAV_ROBOT_MODEL=/home/nvidia/workspaces/microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml
export LIGHTNAV_WALKING_POLICY=/home/nvidia/microduck-course-run/checkpoints/microduck-navigation/alpha_walking.onnx
export LIGHTNAV_OUTPUT=/home/nvidia/microduck-course-run/recordings/lightnav

setsid nohup /home/nvidia/microduck-course-run/envs/notebook/bin/python \
  /home/nvidia/microduck-course-run/run_notebook.py 08 \
  > /home/nvidia/microduck-course-run/08_notebook_rerun.log 2>&1 &
echo "LAUNCHED_08 pid=$!"
