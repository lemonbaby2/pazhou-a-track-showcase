"""Probe stair contacts: is foot_on_floor ever true? Where is the robot?"""
import os
import sys
from pathlib import Path

R = Path("/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-official/experiments/desk-climb")
os.environ.setdefault("ENDING_ROLE", "above")
os.environ.setdefault("LADDER_SHIFT", "0.06")
sys.path.insert(0, str(R / "source" / "src"))
sys.path.insert(0, str(R / "training"))

import numpy as np
import torch

import geometry_patch
import mjlab_microduck.tasks  # noqa
from mjlab_microduck.robot import floor_desk
from mjlab_microduck.tasks import mdp
from mjlab_microduck.tasks.microduck_desk_recovery_env_cfg import make_desk_recovery
from mjlab.envs import ManagerBasedRlEnv
from mjlab.utils.torch import configure_torch_backends

configure_torch_backends()
torch.set_num_threads(1)

cfg = make_desk_recovery(play=True, floor_probability=1.0)
geometry_patch.configure_cfg(cfg)
cfg.sim.nconmax = 512
cfg.seed = 123
cfg.scene.num_envs = 2
cfg.auto_reset = False
cfg.episode_length_s = 5.0
cfg.terminations.pop("reached_top", None)
cfg.events["reset_stair_ladder"].params.update(
    min_start_tread=0, max_start_tread=0, desk_probability=0.0, floor_spawn_prob=1.0
)

env = ManagerBasedRlEnv(cfg=cfg, device="cpu", render_mode=None)
obs, _ = env.reset()
robot = env.scene["robot"]
print("sensors:", list(env.scene.sensors.keys()) if hasattr(env.scene, "sensors") else "n/a")
for name in list(env.scene.sensors.keys()):
    s = env.scene.sensors[name]
    print(f"  {name}: {type(s).__name__}")

act = torch.zeros(cfg.scene.num_envs, 14, device=env.device)
for step in range(24):
    c = mdp._stair_contacts(env)
    keys = {k: (v.float().mean().item() if torch.is_tensor(v) else v) for k, v in c.items()}
    z = robot.data.root_link_pos_w[:, 2].cpu().numpy()
    print(f"step {step:02d} root_z={np.round(z,3)} {keys}")
    if step < 23:
        env.step(act)
print("stair state:", [a for a in dir(mdp._stair_state(env)) if not a.startswith('__')][:20])
