"""结构化日志：控制台可读 + JSONL 可复盘。"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional


class EventLogger:
    def __init__(self, path: Optional[str] = None, echo: bool = True):
        self.path = path
        self.echo = echo
        self.t0 = time.time()
        self.events: list[Dict[str, Any]] = []
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8"):
                pass

    def log(self, step: str, event: str, **data: Any) -> Dict[str, Any]:
        rec = {
            "t": round(time.time() - self.t0, 3),
            "step": step,
            "event": event,
            **data,
        }
        self.events.append(rec)
        if self.echo:
            extra = " ".join(
                "%s=%s" % (k, v) for k, v in data.items() if k not in ("msg",)
            )
            msg = data.get("msg", "")
            line = "[%7.2fs] %-14s %-18s %s %s" % (
                rec["t"], step, event, msg, extra
            )
            print(line.rstrip())
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def summary(self) -> Dict[str, Any]:
        return {
            "events": len(self.events),
            "duration_s": round(time.time() - self.t0, 3),
            "path": self.path,
        }
