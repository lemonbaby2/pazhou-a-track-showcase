"""Patch the ladder video script: allow nconmax/njmax override via env vars."""
from pathlib import Path

p = Path(
    "/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts/scripts/bpu_official_ladder_pair_video.py"
)
src = p.read_text(encoding="utf-8")
anchor = "    geometry_patch.configure_cfg(cfg)\n"
snippet = (
    "    geometry_patch.configure_cfg(cfg)\n"
    "    _ncon = int(os.getenv('MICRODUCK_NCONMAX', '0') or 0)\n"
    "    if _ncon > 0:\n"
    "        cfg.sim.nconmax = _ncon\n"
    "        _nj = int(os.getenv('MICRODUCK_NJMAX', '0') or 0)\n"
    "        if _nj > 0:\n"
    "            cfg.sim.njmax = _nj\n"
    "        print(f'[patch] nconmax={cfg.sim.nconmax} njmax={cfg.sim.njmax}')\n"
)
if "MICRODUCK_NCONMAX" in src:
    print("already patched")
elif anchor not in src:
    raise SystemExit("anchor not found")
else:
    p.write_text(src.replace(anchor, snippet, 1), encoding="utf-8")
    print("patched", p)
    # sanity: importability
    compile(p.read_text(encoding="utf-8"), str(p), "exec")
    print("syntax ok")
