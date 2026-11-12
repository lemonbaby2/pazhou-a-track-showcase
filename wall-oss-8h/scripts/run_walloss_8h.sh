#!/bin/bash
set -u
export PATH="$HOME/.local/bin:$PATH"
export CUDA_HOME=/usr/local/cuda-13
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8
source "$HOME/wallx-env/bin/activate"
cd "$HOME/wall-x"
echo "[$(date -Is)] 8H TRAIN START"
free -g | sed -n 2p
nice -n 10 taskset -c 0-15 torchrun --standalone --nnodes=1 --nproc_per_node=1 wall_x/trainer/fsdp_trainer/train_fsdp.py --config "$HOME/runs/walloss_8h.yml"
echo "[$(date -Is)] 8H TRAIN EXIT=$?"
