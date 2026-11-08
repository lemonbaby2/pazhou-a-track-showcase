#!/usr/bin/env bash
# 一键复现环境：拉上游 microduck_rl → 装依赖 → 打本仓补丁
# 用法：bash scripts/setup_duckrl.sh [目标目录，默认 ~/duck-rl]
set -euo pipefail

DEST="${1:-$HOME/duck-rl}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> 目标目录：$DEST"
if [ -d "$DEST/.git" ]; then
  echo "==> 已存在，跳过 clone"
else
  git clone https://github.com/pollen-robotics/microduck_rl.git "$DEST"
fi

cd "$DEST"

echo "==> 安装 uv（若缺）"
command -v uv >/dev/null 2>&1 || command -v "$HOME/.local/bin/uv" >/dev/null 2>&1 || \
  curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "==> uv sync"
UV_PYTHON=3.12 uv sync

echo "==> 校验 CUDA"
PY="$DEST/.venv/bin/python"
"$PY" - <<'EOF' || echo "  ⚠ torch 无 CUDA，请参照 README「坑」一节替换 torch"
import torch
print("  torch", torch.__version__, "cuda", torch.version.cuda, "avail", torch.cuda.is_available())
EOF

echo "==> 打补丁：环境配置 + 任务注册"
cp "$REPO_ROOT/src/microduck_sprint_env_cfg.py" src/mjlab_microduck/tasks/

INIT=src/mjlab_microduck/tasks/__init__.py
if grep -q "Mjlab-SprintV2-Flat-MicroDuck" "$INIT"; then
  echo "  已注册，跳过"
else
  cat >> "$INIT" <<'PYEOF'


# ---------------------------------------------------------------- sprint (自定义)
from .microduck_sprint_env_cfg import make_microduck_sprint_env_cfg

register_mjlab_task(
    task_id="Mjlab-Sprint-Flat-MicroDuck",
    env_cfg=make_microduck_sprint_env_cfg(preset="v1"),
    play_env_cfg=make_microduck_sprint_env_cfg(play=True, preset="v1"),
    rl_cfg=MicroduckRlCfg,
    runner_cls=MicroduckOnPolicyRunner,
)

register_mjlab_task(
    task_id="Mjlab-SprintV2-Flat-MicroDuck",
    env_cfg=make_microduck_sprint_env_cfg(preset="v2"),
    play_env_cfg=make_microduck_sprint_env_cfg(play=True, preset="v2"),
    rl_cfg=MicroduckRlCfg,
    runner_cls=MicroduckOnPolicyRunner,
)
PYEOF
fi

echo "==> 校验任务注册"
.venv/bin/list-envs 2>/dev/null | grep -i sprint || echo "  ⚠ 未列出 sprint 任务，检查 __init__.py"

echo
echo "完成。下一步："
echo "  cd $DEST"
echo "  MUJOCO_GL=egl .venv/bin/train Mjlab-SprintV2-Flat-MicroDuck --env.scene.num-envs 4096 --agent.max-iterations 3000 --agent.run-name duck_sprint_v2"
