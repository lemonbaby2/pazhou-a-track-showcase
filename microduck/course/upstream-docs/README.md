# 【Datawhale MicroDuck 组队学习】第 85 期学习记录

学习者：patient熬（2 群）。本目录区分课程原始资料、个人笔记与本机生成的实验结果；不把官方预录素材写成个人实测，也不把仿真结果等同于真机指标。

快速复现请从 [START_HERE.md](START_HERE.md) 开始。文档结构对 [Datawhale Hello-Robot](https://github.com/datawhalechina/hello-robot) 的工程化组织方式做了参考，但两个课程的机器人本体、仿真器和运行依赖不同，具体边界见 [HELLO_ROBOT_REFERENCE.md](HELLO_ROBOT_REFERENCE.md)。

| 任务 | 笔记 | 复现入口 | 结果与边界 |
| --- | --- | --- | --- |
| Task1 篮球平衡 | [Task1 学习笔记](task1/Task1_学习笔记.md) | [课程 Notebook](task1/Task1_篮球平衡_Notebook.ipynb)、[安全检查](task1/Task1_safe_check.py) | 61→14 ONNX，250 步/5 秒本机短仿真，0 重置；不是重新训练或真机验证。视频、轨迹和 JSON 在 `task1/`。|
| Task2 浏览器物理扰动 | [Task2 学习笔记](task2/Task2_学习笔记.md) | [课程 Notebook](task2/Task2_浏览器物理扰动_Notebook.ipynb)、[官方教学资料](task2/official_materials/README.md) | 浏览器 MuJoCo 接触/外力交互，具体本机验证和不足见笔记。|

## 运行与来源

Task1 原始 Notebook 的训练与视频格不应直接 `Run All`。公开模型文件并非课程 Notebook 自动生成。安全检查只检查环境定位和模型输入输出；已记录的短仿真结果由独立本机闭环生成。

Task2 源自 [Datawhale Every Embodied 专题](https://github.com/datawhalechina/every-embodied/tree/main/16-%E4%B8%93%E9%A2%98%E7%BB%84%E9%98%9F%E5%AD%A6%E4%B9%A0/05-MicroDuck%E8%BF%90%E5%8A%A8%E7%AD%96%E7%95%A5%E4%B8%8E%E4%BB%BB%E5%8A%A1%E5%BC%80%E5%8F%91%E4%B8%93%E9%A2%98) 与 [mjswan Playground](https://github.com/ttktjmt/mjswan_playground)。课程素材和模型的许可不因放在本仓库而变为仓库根目录的 MIT 许可；详见各任务的来源和许可说明。
