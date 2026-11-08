"""Make mjlab load_env_cfg fall back to env_cfg when a play variant is absent."""
from pathlib import Path

p = Path(
    "/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts/.venv/lib/python3.12/site-packages/mjlab/tasks/registry.py"
)
src = p.read_text(encoding="utf-8")
old = "_REGISTRY[task_name].env_cfg if not play else _REGISTRY[task_name].play_env_cfg"
new = (
    "_REGISTRY[task_name].env_cfg\n"
    "    if not play or _REGISTRY[task_name].play_env_cfg is None\n"
    "    else _REGISTRY[task_name].play_env_cfg"
)
if "_REGISTRY[task_name].play_env_cfg is None" in src:
    print("already patched")
elif old not in src:
    print("anchor not found; current snippet:")
    import re

    m = re.search(r"def load_env_cfg.*?\n(?:.*\n){0,8}", src, re.S)
    print(m.group(0) if m else "n/a")
else:
    p.write_text(src.replace(old, new, 1), encoding="utf-8")
    compile(p.read_text(encoding="utf-8"), str(p), "exec")
    print("patched + syntax ok")
