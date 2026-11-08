#!/bin/bash
# MicroDuck 短跑队列：等当前 sprint 训练退出后，按顺序接后续对照实验。
# 生产优先：每一步开跑前检查 GPU 利用率，生产忙就让路。
# 用法（DGX 上）：setsid nohup bash ~/duck-rl/duck_queue.sh > ~/embodied-harvest/logs/duck_queue.log 2>&1 &
set -u
cd "$HOME/duck-rl" || exit 1
export WANDB_MODE=disabled
export MUJOCO_GL=egl
LOG="$HOME/embodied-harvest/logs"

log() { echo "[$(date '+%F %T')] $*"; }

wait_gpu_idle() {
  for _ in $(seq 1 720); do          # 最多等 6 小时
    U=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
    U=${U:-0}
    [ "$U" -lt 40 ] && { log "GPU 空闲 ($U%)，开跑"; return 0; }
    sleep 30
  done
  log "等待超时，强制开跑（生产仍占 GPU）"
}

# 1) 等主训练退出
while pgrep -f "run-name duck_sprint" > /dev/null; do sleep 60; done
log "主训练 duck_sprint 已结束"

run() {  # run <tag> <task> <extra args...>
  local tag="$1"; shift
  local task="$1"; shift
  wait_gpu_idle
  log ">>> $tag 开始：$task $*"
  .venv/bin/train "$task" --agent.run-name "$tag" --agent.logger tensorboard "$@" \
      > "$LOG/duck_${tag}.log" 2>&1
  log "<<< $tag 退出码 $? （日志 logs/duck_${tag}.log）"
  sleep 60
}

# 2) 记忆型策略：LSTM，扛延迟/遮挡
run sprint_lstm Mjlab-Sprint-Flat-MicroDuck \
    --env.scene.num-envs 2048 --agent.max-iterations 3000 --agent.save-interval 250 \
    --video True --video-length 300 --video-interval 500 \
    --agent.actor.class-name RNNModel --agent.actor.rnn-type lstm

# 3) 官方走路基线（0.4 m/s 上限，用于"冲刺 vs 走路"对照）
run walk_base Mjlab-Velocity-Flat-MicroDuck \
    --env.scene.num-envs 2048 --agent.max-iterations 3000 --agent.save-interval 250 \
    --video True --video-length 300 --video-interval 500

# 5) 粗糙地形抗扰
run rough_perturb Mjlab-Velocity-Rough-MicroDuck \
    --env.scene.num-envs 2048 --agent.max-iterations 2000 --agent.save-interval 250 \
    --video True --video-length 300 --video-interval 500

# 6) 前滚翻（纯娱乐技能，出片用）
run roulade Mjlab-Roulade-Flat-MicroDuck \
    --env.scene.num-envs 2048 --agent.max-iterations 2000 --agent.save-interval 250 \
    --video True --video-length 300 --video-interval 500

log "队列全部完成"
touch "$HOME/embodied-harvest/logs/duck_queue.done"
