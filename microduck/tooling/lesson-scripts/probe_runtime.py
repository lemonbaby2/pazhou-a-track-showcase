"""Runtime probe: where are the ladder/desk bodies in the actual scene?"""
import os
import sys
from pathlib import Path

OFFICIAL_ROOT = Path(
    "/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-official/experiments/desk-climb"
)
os.environ.setdefault("ENDING_ROLE", "above")
os.environ.setdefault("LADDER_SHIFT", "0.06")
sys.path.insert(0, str(OFFICIAL_ROOT / "source" / "src"))
sys.path.insert(0, str(OFFICIAL_ROOT / "training"))

import numpy as np
import torch

import geometry_patch
import mjlab_microduck.tasks  # noqa: F401
from mjlab_microduck.robot import floor_desk
from mjlab_microduck.tasks import mdp  # noqa: F401
from mjlab_microduck.tasks.microduck_desk_recovery_env_cfg import make_desk_recovery
from mjlab.envs import ManagerBasedRlEnv
from mjlab.utils.torch import configure_torch_backends

print("RECORDS:", len(floor_desk.RECORDS))
configure_torch_backends()
torch.set_num_threads(1)

cfg = make_desk_recovery(play=True)
geometry_patch.configure_cfg(cfg)
cfg.seed = 123
cfg.scene.num_envs = 2
cfg.viewer.width = 720
cfg.viewer.height = 540
cfg.viewer.distance = 1.8
cfg.viewer.elevation = -10.0
cfg.viewer.azimuth = 90.0
cfg.viewer.env_idx = 1
cfg.auto_reset = False
cfg.episode_length_s = 5.0
cfg.terminations.pop("reached_top", None)
cfg.events["reset_stair_ladder"].params.update(
    min_start_tread=0, max_start_tread=0, desk_probability=0.0, floor_spawn_prob=1.0
)
for name, default in {"position_noise": 0.004, "yaw_noise_deg": 5.0,
                      "tilt_noise_deg": 2.0, "joint_noise": 0.03,
                      "ladder_y_noise": 0.01}.items():
    cfg.events["reset_stair_ladder"].params[name] = default

print("building env ...")
env = ManagerBasedRlEnv(cfg=cfg, device="cpu", render_mode="rgb_array")
obs, _ = env.reset()
print("entities in scene:", list(env.scene.keys()))

import mujoco

model, data = env.sim.mj_model, env.sim.mj_data
mujoco.mj_forward(model, data)
print("nbody:", model.nbody, "ngeom:", model.ngeom, "nmocap:", model.nmocap)
for name in ["tread_00", "tread_05", "tread_26", "structure", "desktop", "landing_plate", "table_top"]:
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
    if bid < 0:
        print(f"  {name}: MISSING")
        continue
    mocap_id = model.body_mocapid[bid]
    print(f"  {name}: body_id={bid} mocap={mocap_id} xpos={np.round(data.xpos[bid], 3)}")

robot = env.scene["robot"]
print("robot root pos:", np.round(robot.data.root_link_pos_w.numpy(), 3))

frame = env.render()
print("render frame:", None if frame is None else np.asarray(frame).shape)
if frame is not None:
    arr = np.asarray(frame)
    if arr.ndim == 4:
        arr = arr[1]
    from PIL import Image

    Image.fromarray(arr.astype(np.uint8)).save("/tmp/probe_frame.png")
    print("saved /tmp/probe_frame.png")

# unique colours to detect whether any ladder geometry is on screen
print("num geoms with rgba alpha>0:", int((model.geom_rgba[:, 3] > 0.01).sum()))
