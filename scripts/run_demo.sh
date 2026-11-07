#!/usr/bin/env bash
# 本机一键跑通 A 赛道饮品服务仿真
set -e
cd "$(dirname "$0")/.."
python -m sim.run_sim "$@"
echo
echo "产物在 out/ 目录：demo.gif / keyframes.png / timeline.png / run.jsonl"
