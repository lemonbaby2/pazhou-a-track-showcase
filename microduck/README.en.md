# MicroDuck Sprint · Bipedal Duck Locomotion Policy

**Training an 800 g duck to sprint with MuJoCo Warp + PPO on a single DGX Spark.**

> **Headline:** the factory configuration of MicroDuck only commands **±0.4 m/s** (walking).
> This repo pushes it to **0.457 m/s mean / 0.934 m/s single-frame peak** under one fixed protocol
> (command 1.6 m/s, 32 envs, 1200 steps) — a **3.09×** improvement over the first reward recipe.
> It also reports a **negative result**: performance peaks at **iteration 250** and then degrades to
> **0.132 m/s** by iteration 2999. **Training longer is not training faster.**
>
> The community-reported **2.07 m/s** (RTX 4090D, 512 envs, 13500 iterations) is **not reproduced** here.
> No cross-protocol comparison is claimed.

---

## 1. What this is

MicroDuck is an open-source ~25 cm / ~800 g biped from Pollen Robotics: 14 actuated servo joints
(+1 jaw linkage), RK3566 controller, BMI088 IMU, CSI camera, 2S Li-ion pack. Upstream `microduck_rl`
ships a velocity-tracking (walking) task built on [mjlab](https://github.com/mujocolab/mjlab)
(MuJoCo Warp backend) + `rsl_rl` PPO, with a command range of only ±0.4 m/s.

This project adds a **sprint** task on top of it:

| Item | Detail |
|---|---|
| Tasks | `Mjlab-Sprint-Flat-MicroDuck` (v1), `Mjlab-SprintV2-Flat-MicroDuck` (v2) |
| Goal | Straight-line sprint, faster is better; reward flight phase, penalise foot slip and deformed gaits |
| Method | PPO via `rsl_rl`, 4096 parallel envs, MuJoCo Warp (`newton_mjwarp`) |
| Compute | DGX Spark (GB10, 121 GB unified memory, aarch64), single device |
| Outputs | 2 reward recipes, 3000-iteration run, 7 evaluated checkpoints, 144 training clips, 1 two-column manuscript |

**This is not the official project.** It is a derived configuration plus standalone evaluation
scripts. Upstream code is Apache-2.0, © Pollen Robotics.

---

## 2. Results

### 2.1 Same-protocol speed (32 envs × 1200 steps, command 1.6 m/s, first 100 steps discarded)

| Recipe | Checkpoint | cmd (m/s) | mean | median | P95 | peak frame |
|---|---|---:|---:|---:|---:|---:|
| Factory (**command limit only, not measured**) | — | 0.4 | — | — | — | — |
| Sprint **v1** | `model_250` | 1.6 | 0.1481 | 0.1539 | 0.2058 | 0.2507 |
| Sprint **v2** | `model_250` | 1.6 | **0.4572** | **0.4560** | **0.6988** | **0.9335** |
| Sprint v2 | `model_250` | 2.6 | 0.1797 | 0.1780 | 0.3264 | 0.5457 |
| Sprint v2 | `model_2999` | 1.6 | 0.1321 | 0.1215 | 0.2756 | 0.4103 |
| Sprint v1 | `model_750` | 2.6 | 0.0905 | 0.0906 | 0.1646 | 0.2804 |

**v2 / v1 = 3.09×** (0.1481 → 0.4572). All numbers are reproducible from `data/*.json`.

### 2.2 Checkpoint decay (same policy, same test)

| Iteration | 250 | 500 | 1000 | 1500 | 2000 | 2500 | 2999 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mean forward speed (m/s) | **0.4572** | 0.3599 | 0.1872 | 0.1818 | 0.1106 | 0.1216 | 0.1321 |
| Relative to best | 100% | 78.7% | 41.0% | 39.8% | 24.2% | 26.6% | 28.9% |

Training-side evidence: `error_vel_yaw` rises 0.053 → **0.712** (13×) while mean episode reward keeps
climbing (−1.05 → 16.80). The policy learns to twist and hop in place, not to run.

### 2.3 Training metrics (v2, 3000 iterations, 9.1 s/iter, ≈8.3 h)

| Metric | start | end |
|---|---:|---:|
| `track_lin_vel` reward | 0.018 | 2.131 |
| `mean_reward` | −1.05 | 16.80 |
| `mean_episode_length` | 24 | 290.6 |
| `error_vel_yaw` | 0.0534 | **0.7120** |
| `air_time_mean` (s) | 0.0504 | 0.0868 |

> Episode reward and measured speed **decouple**. Never use `mean_reward` as a performance metric here.

---

## 3. Key findings

1. **Reward weights set intent; command range sets the ceiling.** v1 (`air_time` 5.0 > `track_lin` 3.0)
   rewarded standing still and hopping — 0.09 m/s and getting slower. v2 (`track_lin` 6.0, `air_time` 1.0
   with a 0.5 m/s gate) tripled the speed at the same iteration count. Pushing the command to 2.6 m/s,
   outside v2's 0.3–1.6 training range, **dropped** speed to 0.180 — the policy cannot extrapolate.
2. **The optimum is at iteration 250.** Training to 2999 degrades performance by 71%. Without
   mid-training evaluation you will train away your best checkpoint.
3. **Peak ≠ mean.** 0.934 peak vs 0.457 mean — a 2× gap. Public "2.07 / 2.20" figures are instantaneous
   readings; four statistics are reported here to avoid protocol ambiguity.
4. **On aarch64 GB10 the bottleneck is kernel launch overhead, not FLOPs.** 512 envs is not meaningfully
   faster per iteration than 4096; parallelism must be pushed to 4096 to amortise Warp overhead.

---

## 4. Visuals

| Item | File |
|---|---|
| **60 s training montage** (iter 0 → 71500) | [`videos/sprint_progression.mp4`](videos/sprint_progression.mp4) |
| 10 key clips | [`videos/clips/`](videos/clips/) |
| All 144 clips (26 MB) | [`videos/train_clips_full.zip`](videos/train_clips_full.zip) |
| v1 failed run (13 clips) | [`videos/v1_clips.zip`](videos/v1_clips.zip) |
| Reward-hacking diagnosis | `figs/fig2_v1_training.png`, `figs/fig3_reward_imbalance.png` |
| Recipe comparison | `figs/fig4_speed_compare.png`, `figs/fig6_v1_v2_curves.png` |
| Checkpoint decay | `figs/fig7_checkpoint_decay.png` |

---

## 5. Hardware & BOM

Full tables in [`docs/HARDWARE_BOM.md`](docs/HARDWARE_BOM.md).

**Training node (measured):** DGX Spark · GB10 · 20× Cortex-X925 (aarch64) · 121 GB unified memory ·
3.7 TB NVMe · Ubuntu 24.04.4 · CUDA 13.0 · torch 2.11.0+cu130 · MuJoCo 3.10.0 · mjlab + rsl_rl.

**Robot (official public specs, not a purchase list):** ~25 cm / ~800 g (MJCF mass sum 0.737 kg) ·
14 actuated joints (`hip_{yaw,roll,pitch}`, `knee`, `ankle` ×2, `neck_pitch`, `head_{pitch,yaw,roll}`)
· RK3566 @ 50 Hz · BMI088 · IMX219-class CSI camera · 2S Li-ion 7.4 V (8.2 V full, 6.0–6.6 V cutoff).

---

## 6. Layout

```
├── README.md / README.en.md
├── docs/          HARDWARE_BOM · TRAINING_LOG · METRICS_PROTOCOL · experiment_log · style_guide
├── src/           microduck_sprint_env_cfg.py · tasks_init_patch.md · upstream_snapshot/
├── scripts/       probe_sprint_speed · export_sprint_metrics · make_figs · build_paper · setup_duckrl.sh
├── data/          9 JSON files (training curves + per-checkpoint speed)
├── checkpoints/   model_250.pt (best) · model_2999.pt (degraded, kept as evidence)
├── figs/          7 figures
├── videos/        montage · 10 clips · 144-clip zip
└── papers/        two-column manuscript (.docx)
```

---

## 7. Quick start

```bash
git clone https://github.com/pollen-robotics/microduck_rl.git duck-rl
cd duck-rl && uv sync
cp ../src/microduck_sprint_env_cfg.py src/mjlab_microduck/tasks/
cat ../src/tasks_init_patch.md >> src/mjlab_microduck/tasks/__init__.py

MUJOCO_GL=egl WANDB_MODE=disabled .venv/bin/train Mjlab-SprintV2-Flat-MicroDuck \
  --env.scene.num-envs 4096 --agent.max-iterations 3000 \
  --agent.run-name duck_sprint_v2 --agent.logger tensorboard \
  --agent.save-interval 250 --video True --video-length 300 --video-interval 250

.venv/bin/python scripts/probe_sprint_speed.py \
  --ckpt logs/rsl_rl/velocity/<run>/model_250.pt \
  --task Mjlab-SprintV2-Flat-MicroDuck --cmd 1.6 --steps 1200 --num-envs 32 -o speed.json
```

Or run `bash scripts/setup_duckrl.sh` to do all of the above.

---

## 8. Limitations

1. **2.07 m/s not reproduced.** Best mean 0.457 m/s. Gap (env count, iterations, reward design) is not
   quantitatively attributed.
2. **No sim2real.** All results are simulation. MJCF includes 2° backlash and battery-sag randomisation,
   neither validated on hardware.
3. **`model_2999.pt` is degraded** — kept as evidence, not for deployment.
4. **Manuscript is unreviewed** and predates the checkpoint-decay study (see `papers/README.md`).

---

## 9. License

Apache-2.0 (this repository). Upstream `microduck` / `microduck_rl` © Pollen Robotics, Apache-2.0.

```bibtex
@misc{microduck_sprint_2026,
  title  = {MicroDuck Sprint: Reward-Structure Tuning and Evaluation Protocol for
            Bipedal Sprinting Policies in MuJoCo Warp},
  author = {Li, Zipeng},
  year   = {2026},
  note   = {DGX Spark (GB10), mjlab + rsl_rl PPO, 3000 iterations}
}
```
