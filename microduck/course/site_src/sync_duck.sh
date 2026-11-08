#!/usr/bin/env bash
# 同步 MicroDuck 短跑实验室（第十一章）数据到本站并推送到 DGX 局域网副本。
# 用法：bash sync_duck.sh [--no-probe]
#   --no-probe  跳过 DGX 侧测速（省 GPU，只拉已有曲线和视频）
set -euo pipefail

DGX=nvidia@192.168.1.217
SITE="$(cd "$(dirname "$0")" && pwd)"
DUCK="$SITE/duck"
RUN_GLOB='~/duck-rl/logs/rsl_rl/velocity/*duck_sprint'
DO_PROBE=1
[ "${1:-}" = "--no-probe" ] && DO_PROBE=0

mkdir -p "$DUCK/videos"

echo "[1/6] DGX 导出训练曲线"
ssh "$DGX" 'cd ~/duck-rl && .venv/bin/python export_sprint_metrics.py -o ~/duck-rl/logs/sprint_metrics.json' | tail -6

if [ "$DO_PROBE" = "1" ]; then
  CKPT=$(ssh "$DGX" "ls -t $RUN_GLOB/model_*.pt 2>/dev/null | grep -v 'model_0.pt\$' | head -1" || true)
  if [ -n "$CKPT" ]; then
    echo "[2/6] DGX 实测速度：$CKPT"
    ssh "$DGX" "cd ~/duck-rl && .venv/bin/python probe_sprint_speed.py --ckpt '$CKPT' --cmd 2.6 --steps 1000 --num-envs 32 -o ~/duck-rl/logs/sprint_speed.json" | tail -14
  else
    echo "[2/6] 还没到第一个非零 checkpoint，跳过测速"
  fi
else
  echo "[2/6] 跳过测速"
fi

echo "[3/6] 拉取 JSON"
scp -q "$DGX:~/duck-rl/logs/sprint_metrics.json" "$DUCK/" || true
scp -q "$DGX:~/duck-rl/logs/sprint_speed.json" "$DUCK/" 2>/dev/null || true

echo "[4/6] 拉取训练录像"
ssh "$DGX" "ls $RUN_GLOB/videos/train/*.mp4 2>/dev/null" | while read -r f; do
  [ -z "$f" ] && continue
  scp -q "$DGX:$f" "$DUCK/videos/" || true
done
ls -la "$DUCK/videos" | tail -6

echo "[5/6] 重生成第十一章"
( cd "$SITE" && python regen_ch11.py )

echo "[6/6] 推送到 DGX 局域网副本"
ssh "$DGX" 'mkdir -p ~/microduck-site/duck/videos'
scp -q "$SITE/index.html" "$SITE/app.py" "$DGX:~/microduck-site/"
scp -q -r "$DUCK/." "$DGX:~/microduck-site/duck/"
echo "完成。局域网 http://192.168.1.217:8000/ 已更新（uvicorn 直接读盘，无需重启）。"
