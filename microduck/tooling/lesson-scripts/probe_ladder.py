"""Probe the desk-climb scene: are ladder/desk entities actually present?

Import order must mirror scripts/bpu_official_ladder_pair_video.py:
geometry_patch first (it pulls mjlab_microduck.tasks and registers tasks),
then the env cfg modules.
"""
import os
import sys
from pathlib import Path

ROOT = Path("/home/nvidia/microduck-course-run/upstream/official/experiments/desk-climb")
os.environ.setdefault("ENDING_ROLE", "above")
os.environ.setdefault("LADDER_SHIFT", "0.06")
sys.path.insert(0, str(ROOT / "source" / "src"))
sys.path.insert(0, str(ROOT / "training"))

import geometry_patch  # noqa: E402  (mutates floor_desk.RECORDS)
import mjlab_microduck.tasks  # noqa: E402,F401
from mjlab_microduck.robot import floor_desk  # noqa: E402

print("RECORDS count:", len(floor_desk.RECORDS))
names = [r["name"] for r in floor_desk.RECORDS]
print("sample names:", names[:12])
print("tread count:", len([n for n in names if n.startswith("tread_")]))
print("has desktop:", "desktop" in names)
print("has desk_leg:", any(n.startswith("desk_leg") for n in names))

from mjlab_microduck.tasks.microduck_desk_recovery_env_cfg import make_desk_recovery  # noqa: E402

cfg = make_desk_recovery(play=True)
geometry_patch.configure_cfg(cfg)
print("scene entities:", list(cfg.scene.entities.keys()))
for key, ent in cfg.scene.entities.items():
    try:
        spec = ent.spec_fn()
        print(f"  {key}: geoms={len(spec.geoms)} meshes={len(spec.meshes)} bodies={len(spec.bodies)}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {key}: ERROR {type(exc).__name__}: {exc}")
print("viewer:", cfg.viewer)
print("num_envs:", cfg.scene.num_envs)
