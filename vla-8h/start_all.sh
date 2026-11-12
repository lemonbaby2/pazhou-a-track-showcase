#!/bin/bash
# 一次性启动 8h 训练编排 + 常驻监控；两个进程都脱离 SSH 会话
cd /home/nvidia/vla-8h || exit 1
PY=/home/nvidia/wallx-env/bin/python
mkdir -p logs reports figs state outputs

if pgrep -f "vla8h.py orchestrate" > /dev/null 2>&1; then
  echo "orchestrator ALREADY RUNNING"
else
  setsid nohup "$PY" vla8h.py orchestrate >> logs/orchestrator.log 2>&1 < /dev/null &
  echo $! > state/orchestrator.pid
  echo "orchestrator LAUNCHED pid=$!"
fi

sleep 3

if pgrep -f "vla8h.py monitor" > /dev/null 2>&1; then
  echo "monitor ALREADY RUNNING"
else
  setsid nohup "$PY" vla8h.py monitor >> logs/monitor.log 2>&1 < /dev/null &
  echo $! > state/monitor.pid
  echo "monitor LAUNCHED pid=$!"
fi

echo "=== processes ==="
ps -eo pid,etime,args | grep "vla8h.py" | grep -v grep
