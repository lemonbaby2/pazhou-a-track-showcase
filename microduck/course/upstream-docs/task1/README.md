# Task1：篮球平衡

个人笔记：[Task1_学习笔记.md](Task1_学习笔记.md)。本机复现视频：[basketball_gpu_local.mp4](basketball_gpu_local.mp4)。对应机器可读报告：[basketball_gpu_local.json](basketball_gpu_local.json)，轨迹：[basketball_gpu_local.trace.npz](basketball_gpu_local.trace.npz)。

运行记录：61 维观测、14 维关节动作、带 256 维隐状态的 LSTM actor，50 Hz，250 步/5 秒，0 次重置。物理使用 Windows MuJoCo-Warp CPU 后端，ONNX 策略推理使用 RTX 4060；不是 Ubuntu GPU 物理仿真，也不是从零训练或真机成功率。

`Task1_safe_check.py` 检查 ONNX 输入输出，不执行训练和视频格。若旁边没有完整 Datawhale 专题树，环境定位格会明确报告 `not_run`；设置 `MICRODUCK_TOPIC_ROOT` 指向课程专题目录后才能复现该格。本次在 WSL2 Ubuntu 英文路径中的课程完整代码上已通过环境定位格。课程 Notebook 保留原样，避免覆盖预存结果。

`artifacts/basketball/policy.onnx`、`checkpoint.pt` 和 `validation.json` 来自上游公开模型，不是本人训练产物。上游源码归档未重复推送到本仓库；本地完整交付包仍保存 `source.tar.gz`，可按学习笔记的来源重新获取。此目录的上游软件许可见 `LICENSE`，署名见 `NOTICE`；3D 模型资产另受 CC BY-NC-SA 4.0 约束。
