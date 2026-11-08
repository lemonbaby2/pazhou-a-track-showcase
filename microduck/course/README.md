# 课程部分：MicroDuck 8 本 Notebook 全量复现

> 这是 Datawhale 第 85 期 MicroDuck 组队学习的复现归档，与仓库主体的**鸭子短跑策略**（本项目自行训练）是两件事：
>
> - 本目录（`course/`）＝ 跟课复现，使用官方预训练模型，**不训练**
> - 仓库主体（`src/`、`data/`、`videos/sprint_progression.mp4` 等）＝ 本项目自己的 PPO 训练实验

## 一、先看心得

**[Task1-8_学习心得全集.md](Task1-8_学习心得全集.md)** —— 8 本逐本心得，含每本的机制解读、真实执行指标、踩坑记录与边界声明，可直接用于打卡提交。

## 二、8 本索引

| Task | 主题 | 核心机制 | 关键实测 | 边界 |
|---|---|---|---|---|
| 1 | 篮球平衡 | PPO，61 维本体观测 → LSTM → 14 关节 | 1500 步 / 30 s，0 重置，parity 1.19e-6 | 公开权重复现，非从零训练 |
| 2 | 浏览器物理扰动 | MuJoCo WASM + ONNX Runtime Web + WebGL | 63 MB / 48 文件静态应用，48.8 s 录像 | 定性 smoke test，不报成功率 |
| 3 | 高跷行走 | 形态课程：换腿长即换任务 | 9/9 单元格，4.81 MB 视频 | 任务名未注册，走独立 playground |
| 4 | 摆动旋转 | 自激摆动 / 能量泵入（欠驱动） | 9/9 单元格，6.69 MB 视频 | 同上 |
| 5 | 球平衡 | FastSAC，**54 维**观测 | 900 步，parity 2.68e-7，**59 次失败重置** | 稳定性差，如实保留 |
| 6 | 梯面攀爬 | 双策略交接：climber → getup | 1500 步 / 64 env，992 s | `getup` 调用 **0 次**，未触发起身 |
| 7 | RDK X5 / BPU | ONNX → HBM → 端侧推理 | 9/9 单元格，GPU 闭环视频 | **无板，BPU 未验收** |
| 8 | LightNav-0 导航 | 图 + 语言 → 10×3 轨迹 → MPC → 策略 | 三场景全 `model_stop`，残余 1.17–1.87 m | 三场全未到达 |

加餐：`09` 跨缝跳跃（PPO 续训 + ONNX），13/13 单元格，parity 6.6e-6。

## 三、Task8 的核心链条

```text
第一视角图像 + 一句话指令
      ↓ WebSocket
LightNav-0（vLLM 本地推理，不训练）
      ↓ 空间指向通道：目标位置 / 下一步行动位置
      ↓ RVQ 动作码解码 → 10 × 3 局部平面轨迹
MPC（Ipopt）→ 速度命令
      ↓
行走策略（50 Hz 控 14 关节）→ MuJoCo 里真的走起来
```

三场景实测（原始报告见 `validation/lightnav_*_report.json`）：

| 场景 | 预测次数 | 终止 | 推理中位延迟 | 初始距离 | 最终距离 |
|---|---:|---|---:|---:|---:|
| 官方住宅 | 37 | `model_stop` | 1467 ms | 2.946 m | 1.866 m |
| 自建客厅 | 42 | `model_stop` | 1713 ms | 1.811 m | 1.171 m |
| 自建走廊 | 47 | `model_stop` | 1777 ms | 2.700 m | 1.218 m |

**三场都没走到，且都是模型自己喊停。** 这正是 `model_stop ≠ 到达` 的现场证据。

## 三之二、Task8 性能优化（2026-11-04）

针对「三场全没走到」，做了一轮控制层优化实验：**不训练、不改模型权重、不用目标真值**，6 个实验臂 × 3 场景 = 18 组真实运行。

**结果：平均残余距离从 1.477 m 压到 1.127 m，平均改善 21.7%；但三场仍未到达。**

| 场景 | 原版 | 优化后（full_smooth） | 改善 |
|---|---:|---:|---:|
| 官方住宅 | 1.921 m | **1.651 m** | +14.0% |
| 自建客厅 | 1.301 m | **1.096 m** | +15.8% |
| 自建走廊 | 1.209 m | **0.783 m** | +35.2% |

核心发现：

1. **提速无效**——`v_max` 从 0.30 提到 0.55 几乎无变化，因为上游 `MAX_LINEAR_COMMAND = 0.30` 会把命令硬裁掉。
2. **上游把线速度二值化了**——低于 0.08 归零，0.08~0.28 直接抬到 0.28，0.30 以上裁到 0.30。机器人只有「停」和「0.28~0.30」两档速度，这是窄空间绕路的根源。
3. **视觉闭环不能断**——冻结轨迹再走的实验反而更差（客厅 −10.8%），因为失去持续预测后机器人开始原地打转。
4. **真正的瓶颈是出厂行走策略**：命令 0.30 实际只跑出 0.14–0.15 m/s（转化率 52%），24 秒最多走 3.6 m。控制层已穷尽，再提速只能重训策略。

完整报告与 18 组原始数据见 **[optimization/README.md](optimization/README.md)**。

## 四、目录说明

```text
course/
├── Task1-8_学习心得全集.md      # 主文档，8 本心得 + 六条总结
├── notebooks/                   # 10 本执行后 ipynb（00-09，含输出）
│   ├── 00_MuJoCo策略控制_HelloWorld.ipynb
│   ├── 01_篮球平衡_PPO_ONNX_BPU_MuJoCo.ipynb          # Task1
│   ├── 02_浏览器物理扰动_回放与接口.ipynb              # Task2
│   ├── 03_高跷行走_课程与ONNX_BPU.ipynb               # Task3
│   ├── 04_摆动旋转_ONNX_BPU_MuJoCo.ipynb              # Task4
│   ├── 05_球平衡_FastSAC_ONNX_BPU.ipynb               # Task5
│   ├── 06_梯面攀爬_接触与部署模板.ipynb                # Task6
│   ├── 07_RDK网页与多策略_BPU验收.ipynb                # Task7
│   ├── 08_LightNav0_视觉语言导航_GPU_多场景.ipynb      # Task8
│   └── 09_跨缝跳跃_PPO_GPU_ONNX.ipynb                 # 加餐
├── validation/                  # 15 份验收 JSON + 10 份执行记录
│   ├── *_execution.json                 # 每本 notebook 的执行结果（状态/耗时/单元格数）
│   ├── lightnav_*_report.json           # Task8 三场景报告
│   ├── basketball_gpu_latest.json       # Task1
│   ├── stilt_gpu_latest.json            # Task3
│   ├── swing_gpu_latest.json            # Task4
│   ├── ball_balance_gpu_latest.json     # Task5（59 次重置在这里）
│   ├── ladder_gpu_latest.json           # Task6（getup 调用 0 次）
│   ├── walking_gpu_latest.json          # Task7
│   ├── perturbation_gpu_latest.json     # Task2
│   └── long_jump_*.json                 # 加餐 09
├── optimization/                # Task8 控制层优化实验（11-04）
│   ├── README.md                        # 优化报告：诊断、6 臂对照、负结果、边界
│   ├── lightnav_opt.py                  # 优化脚本（参数化 v_max / 停止策略 / 命令整形）
│   ├── reports/                         # 18 组原始 JSON + summary.csv
│   └── videos/                          # 基线 3 段 + 最优组 3 段
└── videos/                      # 17 段课程实拍 MP4
    ├── basketball_gpu_latest.mp4        # Task1
    ├── stilt_gpu_latest.mp4             # Task3
    ├── swing_gpu_latest.mp4             # Task4
    ├── ball_balance_*.mp4               # Task5
    ├── ladder_*.mp4                     # Task6
    ├── walking/perturbation_gpu_latest.mp4  # Task7
    ├── lightnav_*_latest.mp4            # Task8 三场景
    └── long_jump_*.mp4                  # 加餐 09
```

> Notebook 是**执行后**版本（带输出），体积 17 MB 主要来自内嵌视频帧与图表。要看干净源码，可在 Jupyter 里 `Cell → All Outputs → Clear` 后保存副本。

## 四之二、同一批内容在三个平台上的位置

这 8 个任务的内容分布在三个地方，**结构不一致，看之前先对一下表**：

| 平台 / 位置 | 结构 | 覆盖 | 说明 |
|---|---|---|---|
| **Gitee** `duckf--the-playful-duck` · `course/` | 扁平目录，按 Task 编号索引 | Task1–8 + 加餐 | 心得 + notebook + JSON + MP4 全在，**本文件所在处** |
| **GitHub** `lemonbaby2/-123` · `main` 分支 | `datawhale_microduck/task1`、`task2` | **只有 Task1、Task2** | 默认分支看不到 Task3–8 |
| **GitHub** `lemonbaby2/-123` · `microduck-task2` 分支 | `datawhale_microduck/task3/notebooks/` 下 00–09 | Task1–8 + 加餐 | 8 个 Task 打包在单个 `task3` 目录里，没有独立的 task4–task8 目录 |

**结论：课程意义上的「8 个 Task」没有拆成 8 个独立目录或仓库。** GitHub 上是「task1 / task2 各一目录 + task3 一个全量包」，Gitee 上是「course/ 一个归档目录」。要按 Task 逐本找，用 `notebooks/` 里的编号前缀定位最快。

> Gitee 的 Markdown 不支持内嵌 mp4，点击文件名下载后播放。如需在线播放，见下方「相关链接」。

## 五、相关链接

| 内容 | 地址 |
|---|---|
| 课程仓库（8 本 Notebook 原始材料） | https://github.com/datawhalechina/every-embodied |
| 在线仿真器（浏览器直接玩） | https://huggingface.co/spaces/pollen-robotics/microduck-simulator |
| MicroDuck 开源主页 | https://pollen-robotics.com/microduck |
| LightNav-0 官方代码 | https://github.com/lightorigins/LightNav-0 |

## 六、执行环境

| 项 | 值 |
|---|---|
| 算力节点 | NVIDIA DGX Spark（GB10 Grace-Blackwell，aarch64，sm_121） |
| 统一内存 | 121 GB |
| CUDA | 13.0 |
| 系统 | Ubuntu 24.04.4 LTS |
| 课程代码提交 | `b11ee54ad51260abbe230446c22e528133e05ab9` |

## 七、诚实边界

1. **Task3 / Task4 的 mjlab 任务名未注册。** notebook 里 `--task Mjlab-Stilt-Flat-MicroDuck`、`Mjlab-SwingPump-MicroDuck` 都会报 `invalid choice`，因为 MicroDuck 任务没进 mjlab 注册表（内置只有 12 个通用任务）。视频由独立 playground 的 ONNX 闭环生成。单元格显示 9/9 全绿，但异常在 log 里——**`executed` 不等于成功**。
2. **Task5 球平衡 900 步重置 59 次**，策略并未稳定收敛。视频片段好看，但重置次数才是真实指标。
3. **Task6 的 `getup` 策略本次调用 0 次**，双策略只用了其中一套。
4. **Task7 没有 RDK X5 硬件**，BPU 端侧推理、HBM 编译、板端审计全部未做，执行记录标记为 `bpu: not_run_no_board`。GPU 闭环视频不能替代板端结果。
5. **Task8 三场景全部未到达目标**，残余距离 1.17–1.87 m，结果原样保留，未挑选片段。

以上都不是「操作失误」，而是这套系统真实的能力边界。写清楚比写好看有用。

## 八、许可

课程 Notebook、官方模型、场景网格与教学素材的版权归 Datawhale / Pollen Robotics / LightNav-0 作者所有，本目录仅作学习复现归档，不改变其原始许可。仓库自行编写的心得文本与实验数据遵循仓库根目录 Apache-2.0。
