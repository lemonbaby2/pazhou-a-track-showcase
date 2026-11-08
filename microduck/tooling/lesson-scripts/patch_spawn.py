"""Patch ladder video script: make spawn distribution configurable via env vars."""
from pathlib import Path

p = Path(
    "/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts/scripts/bpu_official_ladder_pair_video.py"
)
src = p.read_text(encoding="utf-8")
anchor = """    cfg.events["reset_stair_ladder"].params.update(
        min_start_tread=0,
        max_start_tread=0,
        desk_probability=0.0,
        floor_spawn_prob=1.0,
    )
"""
new = """    _start = int(os.getenv("MICRODUCK_LADDER_START_TREAD", "0") or 0)
    _floor = float(os.getenv("MICRODUCK_LADDER_FLOOR_PROB", "1.0") or 1.0)
    cfg.events["reset_stair_ladder"].params.update(
        min_start_tread=_start,
        max_start_tread=_start,
        desk_probability=0.0,
        floor_spawn_prob=_floor,
    )
    print(f"[patch] spawn tread={_start} floor_prob={_floor}")
"""
if "MICRODUCK_LADDER_START_TREAD" in src:
    print("already patched")
elif anchor not in src:
    raise SystemExit("anchor not found")
else:
    p.write_text(src.replace(anchor, new, 1), encoding="utf-8")
    compile(p.read_text(encoding="utf-8"), str(p), "exec")
    print("patched + syntax ok")
