# MicroDuck Task1 / Task2 启动入口

本目录保存第 85 期 Datawhale MicroDuck 组队学习的两项独立实验。建议在 WSL2 Ubuntu 的英文路径运行，避免 MuJoCo XML 解析器受 Windows 中文路径影响。

## Task1：篮球平衡

Task1 的安全验证只检查 Notebook 环境定位与公开 ONNX 策略契约，不启动训练，也不会覆盖 Notebook 的预存结果。

```bash
python -m venv .venv-task1
source .venv-task1/bin/activate
python -m pip install --upgrade pip
python -m pip install jupyterlab onnx
python datawhale_microduck/task1/Task1_safe_check.py
jupyter lab --no-browser --ip=127.0.0.1
```

模型契约应为 `61` 维观测输入、`14` 维动作输出。训练、视频生成等需要缺失模型或 GPU 的格子不要直接 `Run All`。

## Task2：浏览器物理扰动

Task2 仓库保存笔记、Notebook、录屏脚本与个人实验结果；完整的 mjswan WASM 构建仍按上游项目生成，不在这里重复分发第三方构建产物。

已构建目录可用仓库内服务器启动：

```bash
python datawhale_microduck/task2/official_materials/serve_mjswan.py \
  --directory /home/lizp/microduck-task2/dist/microduck \
  --host 127.0.0.1 \
  --port 8092
```

然后打开：

```text
http://127.0.0.1:8092/?scene=duck&policy=walk
```

若本机的构建输出目录不同，只需修改 `--directory`。页面成功加载后应能读取 MuJoCo WASM、`scene.mjz`、`walk.onnx`、观测模型和终止条件模型。

## 当前交付状态

- Task1：Notebook、公开模型、校验脚本、5 秒闭环视频、轨迹和 JSON 报告齐全。
- Task2：Notebook、构建/服务说明、48.8 秒三次扰动录像、关键帧和 JSON 报告齐全。
- 所有仿真结果只证明对应软件环境中的定性行为，不代表真机鲁棒性。

