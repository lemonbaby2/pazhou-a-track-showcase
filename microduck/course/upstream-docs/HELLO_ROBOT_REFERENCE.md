# Hello-Robot 工程组织参考

参考仓库：[datawhalechina/hello-robot](https://github.com/datawhalechina/hello-robot)，核对版本 `main`（2026-10-16 获取）。

Hello-Robot 面向 Isaac Sim、ROS 2 与 G2 机器人，MicroDuck 任务面向 MuJoCo、ONNX 策略与浏览器物理扰动，两者不是同一套运行环境。因此本仓库只借鉴其“项目概览 → 环境 → 运行 → 实验结果 → 边界与来源”的文档结构，不复制其教程代码，也不把 Isaac Sim/G2 的结果写成 MicroDuck 实验结果。

本交付中的对应关系如下：

| Hello-Robot 的组织思路 | MicroDuck 落地 |
| --- | --- |
| 章节入口清晰 | `task1/README.md`、`task2/README.md` |
| 可运行代码与说明并列 | Notebook、验证/录屏脚本、`START_HERE.md` |
| 结果素材可追溯 | 视频、关键帧、轨迹、JSON 报告 |
| 明确仿真与真机边界 | 两篇学习笔记均标注定性 smoke test 的限制 |
| 第三方资产单独说明 | Task1 `LICENSE`/`NOTICE`，Task2 上游链接与来源说明 |

分支约定：

- `microduck-task1`：Task1 篮球平衡的提交与启动入口；
- `microduck-task2`：Task2 浏览器物理扰动的提交与启动入口；
- `main`：保留两个任务的总索引与完整归档。

