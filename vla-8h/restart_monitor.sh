#!/bin/bash
# Restart ONLY the monitor using its recorded pid (never pkill -f: it kills this shell).
R=/home/nvidia/vla-8h
P=$(cat "$R/state/monitor.pid" 2>/dev/null)
if [ -n "$P" ]; then
  kill "$P" 2>/dev/null || true
  echo "killed old monitor pid=$P"
fi
sleep 2
rm -f "$R/reports/FAILED.md"
echo "removed stale FAILED.md"
bash "$R/start_all.sh"
echo "=== after ==="
ps -eo pid,etime,args | grep "vla8h.py" | grep -v grep
