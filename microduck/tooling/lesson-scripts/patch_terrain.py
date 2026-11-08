"""Fix the floor-spawn false 'airborne' bug in the ladder video script.

Two root causes:
1. mdp._stair_geom_ids() finds the floor by looking up a body literally named
   "terrain".  The desk-climb scene never creates one, so ids["terrain"] is
   empty and foot_on_floor is always False.
2. Every spawn drops ~0.7 m, which burns the 18-step airborne grace window and
   terminates the episode at step 19 before the robot can stand.

Fix: add a flat plane terrain entity + widen the airborne grace window.
"""
from pathlib import Path

p = Path(
    "/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts/scripts/bpu_official_ladder_pair_video.py"
)
src = p.read_text(encoding="utf-8")

anchor = "    print(f'[patch] nconmax={cfg.sim.nconmax} njmax={cfg.sim.njmax}')\n"
snippet = """    print(f'[patch] nconmax={cfg.sim.nconmax} njmax={cfg.sim.njmax}')
    # --- terrain + airborne fix ---
    if getattr(cfg.scene, 'terrain', None) is None:
        from mjlab.terrains.terrain_entity import TerrainEntityCfg
        cfg.scene.terrain = TerrainEntityCfg()
    cfg.scene.terrain.terrain_type = 'plane'
    cfg.scene.terrain.terrain_generator = None
    _term = cfg.terminations.get('airborne')
    if _term is not None:
        _p = dict(_term.params or {})
        _op = dict(_p.get('original_params') or {})
        _op['grace_steps'] = int(os.getenv('MICRODUCK_AIRBORNE_GRACE', '80') or 80)
        _p['original_params'] = _op
        _term.params = _p
        print(f'[patch] airborne grace_steps={_op["grace_steps"]}')
    print(f'[patch] terrain={cfg.scene.terrain.terrain_type}')
"""

if "airborne grace_steps" in src:
    print("already patched")
elif anchor not in src:
    raise SystemExit("anchor not found (run patch_nconmax.py first)")
else:
    p.write_text(src.replace(anchor, snippet, 1), encoding="utf-8")
    compile(p.read_text(encoding="utf-8"), str(p), "exec")
    print("patched + syntax ok")
