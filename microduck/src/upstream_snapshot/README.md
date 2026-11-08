# 源码快照（上游 + 本仓补丁，只读参考）

来源：DGX 上实际用于训练的 `~/duck-rl` 工作树（克隆自 `github.com/pollen-robotics/microduck_rl`，Apache-2.0，© Pollen Robotics）
打包时间：2026-11-02

## 这里是什么

**训练现场的原样快照**，即"上游代码 + 本仓补丁"的合并状态。所以你能直接看到：

| 文件 | 状态 |
|---|---|
| `src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py` | 上游原版（走路任务，命令 ±0.4 m/s）—— 本仓配方的派生基类 |
| `src/mjlab_microduck/tasks/microduck_sprint_env_cfg.py` | **本仓新增**（v1/v2 两个 preset） |
| `src/mjlab_microduck/tasks/__init__.py` | **已打补丁**，末尾含 2 个 sprint 任务的注册 |
| 其余 `*.py` / `*.xml` / `*.json` | 上游原版，未改动 |

对照方式：`diff` 一下 `microduck_velocity_env_cfg.py` 与 `microduck_sprint_env_cfg.py`，就能看出改了哪些奖励项、命令区间和回合长度。

## 缺什么

**已剔除**：`robot/*/assets/` 下的网格与贴图（STL/OBJ/PNG，约 26 MB）。缺了这些，MJCF 无法加载——这是有意的，避免仓库被二进制资源撑大。

**怎么补**：

```bash
git clone https://github.com/pollen-robotics/microduck_rl.git duck-rl
# 把本快照的补丁文件覆盖过去
cp src/upstream_snapshot/src/mjlab_microduck/tasks/microduck_sprint_env_cfg.py \
   duck-rl/src/mjlab_microduck/tasks/
# __init__.py 里的注册段落照抄追加（见 ../tasks_init_patch.md）
```

## 未包含

训练日志（`logs/`）、虚拟环境（`.venv/`）、检查点原始目录。前者已在 `data/` 转成 JSON，后者只保留最佳与末期两个权重在 `checkpoints/`。
