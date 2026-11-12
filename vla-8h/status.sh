#!/bin/bash
R=/home/nvidia/vla-8h
echo "=== state ==="
head -6 "$R/state/status.json"
echo "=== orchestrator ==="
tail -8 "$R/logs/orchestrator.log"
echo "=== processes ==="
ps -eo pid,pcpu,pmem,etime,args | grep -E "lerobot_train|vla8h.py" | grep -v grep | cut -c1-145 | head -6
echo "=== smoke log tail ==="
tail -c 1600 "$R/logs/train_smoke.log"
echo
echo "=== loss count ==="
grep -c 'loss:' "$R/logs/train_smoke.log"
echo "=== recent loss ==="
grep -oE 'loss:[0-9.]+ grdn:[0-9.]+ lr:[0-9.eE+-]+ updt_s:[0-9.]+' "$R/logs/train_smoke.log" | tail -3
echo "=== monitor snapshot ==="
ls -la "$R/reports/" | tail -8
