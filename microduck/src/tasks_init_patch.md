# 任务注册补丁

上游 `microduck_rl` 的任务注册在 `src/mjlab_microduck/tasks/__init__.py` 末尾。
把本仓的 `microduck_sprint_env_cfg.py` 复制进同目录后，追加下面两段即可。

```python
# ---------------------------------------------------------------- sprint (自定义)
from .microduck_sprint_env_cfg import make_microduck_sprint_env_cfg

# v1：第一版配方（已被实测证明会 reward hacking —— 站着刷腾空分）
register_mjlab_task(
    task_id="Mjlab-Sprint-Flat-MicroDuck",
    env_cfg=make_microduck_sprint_env_cfg(preset="v1"),
    play_env_cfg=make_microduck_sprint_env_cfg(play=True, preset="v1"),
    rl_cfg=MicroduckRlCfg,
    runner_cls=MicroduckOnPolicyRunner,
)

# v2：修正版（速度权重 6.0、腾空降权提阈、命令课程 0.3–1.6）
register_mjlab_task(
    task_id="Mjlab-SprintV2-Flat-MicroDuck",
    env_cfg=make_microduck_sprint_env_cfg(preset="v2"),
    play_env_cfg=make_microduck_sprint_env_cfg(play=True, preset="v2"),
    rl_cfg=MicroduckRlCfg,
    runner_cls=MicroduckOnPolicyRunner,
)
```

## 验证

```bash
.venv/bin/list-envs | grep -i sprint
# 期望输出：
#   Mjlab-Sprint-Flat-MicroDuck
#   Mjlab-SprintV2-Flat-MicroDuck
```

## 注意

- `task_id` 必须带引号。裸字符串写 `task_id=Mjlab-Sprint-...` 会被解析成变量相减而报 `NameError`。
- `register_mjlab_task` 需要 `train_cli.py` 的注册表已加载，**追加在文件末尾**即可，不要插到中间。
- 若只想跑 v2，可以只追加第二段；但对照实验需要 v1 时再补上。
