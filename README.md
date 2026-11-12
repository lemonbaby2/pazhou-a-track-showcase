# 琶洲算法大赛 2026 · A 赛道（二次开发技术）· 商业饮品服务

> 把「夹空托盘 → 抓 2 瓶水装盘 → 端盘导航 → 逐份上桌 + 语音通知」做成分层、可恢复、可对接官方 SDK 的任务工程。
> **没有机器人也能在本机完整跑通**（仿真后端），有机器人时只换适配器。

## 2026-11-12 新增：π0.5 3.6B · 8 小时连续训练看板与全量归档

> **状态：已完成。** 编排器 2026-11-11 20:23:14 结束，4 个消融臂全部跑完，GPU 已空闲。

- **实时看板**：[π0.5 8h 连续训练看板](https://lemonbaby2.github.io/pazhou-a-track-showcase/vla-8h.html)（5 分钟自动刷新，站点导航已挂「π0.5 实时看板」入口）
- **全量归档**：[`vla-8h/`](vla-8h/) —— 20 文件 / 1.47 MB，含实验协议、4 臂结果、逐条指标 `metrics.jsonl`、原始训练日志与 loss 曲线；逐字节镜像自 DGX `~/vla-8h/`，**只读拉取，未改动 DGX 任何进程或配置**
- **完整说明与复现步骤**：[`vla-8h/README.md`](vla-8h/README.md)
- **配套代码**：[`scripts/vla8h_orchestrator.py`](scripts/vla8h_orchestrator.py)（编排器）、[`scripts/vla8h_dashboard.py`](scripts/vla8h_dashboard.py)（看板生成 + 推送），均与运行版本 MD5 一致

| 臂 | 自变量 | 终止码 | loss 首 → 末 | 完成步数 |
|---|---|---:|---:|---:|
| `A_ki` | 基线 Knowledge Insulation + QUANTILES | 0 | 0.463 → 0.210 | 4015 / 4015 |
| `B_lm` | 解冻 VLM 语言模型 | **124** | 0.454 → 0.167 | **2974 / 4015（超时截断）** |
| `C_mstd` | QUANTILES → MEAN_STD | 0 | 0.860 → 0.420 | 4015 / 4015 |
| `D_beta` | Beta(1.5,1.0) → 均匀采样 | 0 | 0.449 → 0.224 | 4015 / 4015 |

**边界**：8 小时只是少步数微调，**未复现论文榜单数值**；四臂 loss 起始值不同，不可横向比绝对值。
`B_lm` 的 `rc=124` 是时间预算切断（非崩溃），其数据只作趋势参考。loss 全部由训练日志正则解析，原始日志已入库可复核。

**看板访问排查**：若浏览器打不开，先直连验证服务端
`curl --noproxy '*' -I https://lemonbaby2.github.io/pazhou-a-track-showcase/vla-8h.html`（返回 `200 OK` 即服务端正常）。
本机浏览器打不开通常是缓存了已失效的本地代理端口，**先重启 Chrome**，再用临时 profile 复验；代理端口会变，不要写死。

---

## 2026-11-07 公开资料包

- **展示站：**[琶洲 A 赛道资料与验证面板](https://lemonbaby2.github.io/pazhou-a-track-showcase/)
- **三分钟视频：**[普通话旁白 MP4](site/downloads/pazhou_a_showcase_3min.mp4)
- **数据资料：**[`data_registry/`](data_registry/) 收录 ALOHA Mobile Wipe Wine 与 ALOHA Static Coffee 的固定 revision、SHA-256 清单、下载脚本、质量检查脚本和训练日志。
- **实验记录：**[`docs/开源真机数据与赛题适配_20261107.md`](docs/开源真机数据与赛题适配_20261107.md) 与 [`docs/赛题本地规则测试记录_20261107.md`](docs/赛题本地规则测试记录_20261107.md)。
- **验证范围：**GPU 回归实验使用外部 ALOHA 状态—动作数据，不是比赛策略或真机成绩；任务仿真为 CPU 2D mock，不是 Isaac Sim 或官方计分器。
- **数据体积：**原始公开数据约 2.86 GB，不纳入 Git 仓库；使用 `data_registry/download_datasets.py` 在本地按固定 revision 下载并校验。数据来源及许可说明见数据目录的 README。

> 展示站已通过 GitHub Pages workflow 部署。Cloudflare 临时预览仍可能在未认领时过期。

## 2026-11-09 新增：MicroDuck 技术储备全量归档

- **展示页：**[MicroDuck 技术储备 · 实测指标与归档](https://lemonbaby2.github.io/pazhou-a-track-showcase/microduck.html)（已从本站导航进入）
- **全量归档：**[`microduck/`](microduck/) —— **362 文件 / 144.29 MB**，逐文件 SHA-256 清单见 [`microduck/MANIFEST.csv`](microduck/MANIFEST.csv)
- **内容边界：**这是**独立于 A 赛道赛题的具身智能能力储备**，不是比赛策略、不是官方计分结果。A 赛道使用统一轮式人形平台，与 25 cm 双足 MicroDuck 不同构，两套数字不得混用。

| 板块 | 关键结果 | 最重要的负面结论 |
|---|---|---|
| 短跑策略（自训 PPO / MuJoCo Warp） | 同口径 0.1481 → **0.4572 m/s（3.09 倍）** | 训练到 3000 轮**退化到 0.1321 m/s**，最佳在 iter 250 |
| Datawhale 8 本 Notebook 复现 | 10 本 notebook 全部执行、8 篇心得全集 | 9/9 全绿但任务未注册；球平衡 59 次重置；爬梯 `getup` 零调用 |
| Task8 LightNav-0 控制层优化 | 18 组实验，平均残余距离**改善 21.7%** | 三场景**仍然全部没走到**，根因是出厂策略 0.14–0.15 m/s 步态上限 |
| 双栏论文稿与写作知识库 | A4 双栏 docx（4 表 5 图 13 式 17 引用） | 定稿于 10-30，**未含**退化实验与 Task8 优化两节 |

三份必读文档：[总索引](microduck/README.md) · [全部性能指标](microduck/METRICS.md) · [建议与决策台账](microduck/RECOMMENDATIONS.md)。

> 归档内含大体积 MP4，但**不放在 `site/` 下**（`scripts/verify_public_package.py` 对站点单文件有 5 MiB 限制）；展示页的视频走仓库外链。仓库原有 CI（pytest + 仿真冒烟）不受影响。

---

## 0. 结论先行：本机哪个项目最适合？

先说结论：**没有一个现成项目能直接改造成 A 赛道**，因为 A 赛道用的是主办方**统一的轮式人形平台**（轮式底盘 + 人形半身 + 双指夹爪），接口由主办方公布、现场禁网禁云端 AI。但本机资产可以这样复用：

| 本机项目 | 形态 | 与 A 赛道的关系 | 结论 |
|---|---|---|---|
| **图灵手臂 `lingbot_real`**（bobac3） | RealMan 单臂 + RGB-D，`pick_place`/`pour`/`handover`，VLA 数据采集 | **操作能力最接近**（抓取/放置/上饮）；但没有底盘导航、托盘、语音 | ✅ 作「操作核心」参考 |
| **`MicroDuck_Task2_Deploy`** | 25 cm 双足，Rust `robotd`/`odometry`/`duck-detect`/`sounds` | **移动部署/语音框架最接近**；但没有双指夹爪、人形上半身、托盘 | ✅ 作「移动部署 + 语音」参考 |
| `MicroDuck_Task1` | 具身智能学习资料库（20+ 章） | 不是工程 | ❌ 不适用 |
| `琶洲算法大赛2026_具身智能世界模型` | 世界模型 / 视频生成 / PAOS Skill **另一个赛道** | 与 A 赛道不同赛题 | ❌ 不适用 |
| `gpu_remote` | GPU 远程控制台（本机新做） | 与赛题任务无关，但可远程用本机 GPU 训练 | ❌ 不适用 |

**所以本仓库的做法是**：新建一个**平台无关的任务层**，把图灵手臂的「抓取—放置」操作逻辑、MicroDuck 的「移动—部署—语音」框架合并，并对官方 SDK 留出适配口。这也是「二次开发」最稳的落点：**平台换、任务层不换**。

> 为什么不直接搬图灵手臂？平台不同（固定 RealMan 臂 vs 轮式人形），且现场接口由主办方提供、禁止云端 AI；直接搬会水土不服。它的价值在**操作时序与异常恢复经验**，不在代码本身。

---

## 1. 赛题要点（硬约束）

| 项 | 要求 |
|---|---|
| 平台 | 统一轮式人形（轮式底盘 + 人形半身 + 双指夹爪），主办方提供电脑/地图/预置环境 |
| 任务 | 赛前夹稳空托盘 → 待命区出发 → 备餐台抓 2 瓶水装盘 → 端盘导航到客人桌 → 逐份上桌 + 语音通知 |
| 时间 | 每队总赛时 90 分钟；单轮规定 5 分钟；至少 1 轮、最多 2 轮，取高分、不跨轮拼接 |
| 评分 | 基础 100 分：场景操作 75 + 任务五 15 + 任务六 10（细则另行公布） |
| 禁止 | 现场离线；禁止联网求助 / 云端 AI；不得绕过安全限位、改未开放系统、加未经许可硬件 |
| 选手负责 | 位置标定、感知识别、动作调用与调整、任务调度、异常恢复、程序部署 |

完整提炼见 [`docs/赛题解读.md`](docs/赛题解读.md)。

---

## 2. 本机 60 秒跑通

```bash
pip install -r requirements.txt

# 默认演示（seed=1，会触发一次托盘倾角超限 → 调平恢复）
python -m sim.run_sim

# 抓取失败恢复样本
python -m sim.run_sim --seed 7 --out out/seed7

# 单元测试
python -m pytest -q
```

Windows 也可双击 `scripts/run_demo.bat`；有 make 时 `make test` / `make demo` / `make all`。

产物在 `out/`：

| 文件 | 内容 |
|---|---|
| `demo.gif` | 任务全程俯视演示（含 HUD：状态 / 用时 / 托盘倾角 / 四步进度） |
| `keyframes.png` | 4 个关键帧（含**最大倾角那一帧**） |
| `timeline.png` | 状态时间线 |
| `run.jsonl` | 结构化事件日志，可复盘每一步与每次恢复 |

实测结果（seed=1）：**桌面 2/2 瓶、任务 DONE、仿真用时 24.4 s（上限 300 s）、最大倾角 12.2° 并成功调平恢复**；20 个随机种子全部成功（100%）。

---

## 3. 示教数据采集与质检（备赛新增）

赛题评分 75 分在场景操作，长期看只有「示教 → 模仿学习 → 真机回归」这条线能稳住成功率。
本仓库提供**零第三方依赖**的采集与质检链路，现场网络不可控时也能把数据留下来。

```bash
# 一条命令：跑仿真 → 按技能段切成 episode → 落盘 → 立即质检
python -m scripts.record_episode --out data/raw --episodes 3 --seed 1 --min-frames 4 --qc

# 单独质检（真机数据建议开 --joint-limit，能抓出"把度当弧度"的低级错）
python -m scripts.check_dataset --root data/raw --joint-limit 3.2 --min-episodes 50
```

| 产物 | 内容 |
|---|---|
| `data/raw/meta/info.json` | 任务、帧率、相机、**代码 commit**、状态/动作语义 |
| `data/raw/meta/episodes.jsonl` | 每条的成功标记、帧数、时长、**sha256** |
| `data/raw/episodes/episode_XXXXXX/` | `frames.jsonl`（逐帧 t/state/action）+ `meta.json`（指令/标签/成败） |
| `out/qc_report.json` | 质检报告，可直接进 CI |

质检判据（`E_` 阻塞、`W_` 提示）：空录、超长、时间戳回退、丢帧率、动作静止、动作跳变、关节量纲、时长过短、条数不足。

完整流程见 **[`docs/真机数据采集SOP.md`](docs/真机数据采集SOP.md)**（七阶段：任务定义 → 硬件相机 → 标定 → 采集 → 质检 → 归档 → 训练回归）。
开源生态与选型结论见 **[`docs/开源生态选型.md`](docs/开源生态选型.md)**（含"你的卡能训完哪个模型"的实测门槛表）。

---

## 4. 架构

```
config/task.yaml          场地坐标 / 阈值 / 重试次数 / 随机失败率
bev/
  interfaces.py           5 个平台无关接口：Nav / Arm / Gripper / Vision / Voice
  task.py                 任务状态机 + 异常恢复（核心）
  tray.py                 托盘倾角监控（按峰值判定）
  dataset.py              示教数据采集器 + 质检器（纯标准库，LeRobot 友好）
  perception.py           MockVision（真值）+ YoloVision（预留）
  voice.py                MockVoice / SapiVoice（Windows 离线）
  mock_world.py           二维仿真世界（导航/机械臂/夹爪/倾斜）
  adapters/vendor_sdk.py  官方 SDK 适配模板（待接口公布）
  logger.py               JSONL + 控制台日志
sim/
  render.py               PIL 渲染俯视图 + HUD
  run_sim.py              仿真入口
scripts/
  record_episode.py       采集 / 回放：按技能段切 episode 并落盘
  check_dataset.py        数据集质检 CLI（可进 CI）
tests/
  test_task.py            6 项状态机/恢复单测
  test_dataset.py         11 项采集/质检单测
docs/                     赛题解读 / 方案设计 / 接口对接 / 比赛日手册 / 评分对齐
                          + 开源生态选型 / 真机数据采集SOP
```

**分层原则**：任务层只依赖 `bev/interfaces.py`。换平台 = 换 `adapters`，`task.py` 一行不改。

---

## 5. 任务状态机

| 状态 | 动作 | 失败恢复 |
|---|---|---|
| `BOOT` | 自检（托盘夹稳、2 瓶就位） | — |
| `ANNOUNCE` | 语音播报开始服务 | — |
| `NAV_PREP` | 导航到备餐台 | 重试 ≤2 次，回 home 重新定位 |
| `DETECT` | 检测 2 瓶饮品 | 不足 2 瓶直接中止 |
| `PICK_PLACE_1/2` | 抓瓶 → 抬起 → 放托盘 | 抓取重试 ≤3；释放失败重复开爪 ≤3 |
| `NAV_GUEST` | 端盘导航到客人桌 | 倾角超限 → 调平 → 继续；导航失败重试 |
| `SERVE_1/2` | 取瓶 → 放桌 → 语音 | 取瓶/放稳各重试 ≤3 |
| `DONE` | 语音结束播报 | — |
| `ABORT` | 语音报警 + 记录原因 | — |

关键设计：**托盘倾角按「自上次复位以来的峰值」判定**。只读最后一帧的瞬时值会漏掉导航途中的瞬时倾斜（这是本工程实际踩过的坑）。

---

## 6. 评分对齐

| 评分方向 | 代码位置 | 验证证据 |
|---|---|---|
| 启动与定位 | `ANNOUNCE` + `_nav` | `run.jsonl` 的 `announce`/`nav_ok` |
| 饮品抓取与装盘 | `_pick_and_place` | 2 次 `grasp_ok` + `place_ok` |
| 端盘导航配送 | `NAV_GUEST` + `TrayMonitor` | `max_tilt_deg`、`tilt_recovered` |
| 桌面上饮与语音 | `_serve` | 2 次 `served` + 2 条语音 |
| 过程稳定性 | 全程重试/恢复计数 | `nav_retries`/`grasp_failures`/`tilt_recoveries` |
| 职业素养（任务五/六，待细则） | 结构化日志 + 标准化操作 | `run.jsonl` 可逐条复盘 |

详见 [`docs/评分对齐表.md`](docs/评分对齐表.md)。

---

## 7. 接入官方 SDK

接口公布后只需三步：

1. 打开 `bev/adapters/vendor_sdk.py`，按 5 个类填 TODO；
2. `io = build_robot_io(sdk)`；
3. `BeverageTask(io, cfg, log, tray).run()`。

任务层与仿真层零改动。标定与联调步骤见 [`docs/接口对接指南.md`](docs/接口对接指南.md)。

---

## 8. 还能怎么变强（可选）

- **抓取策略升级**：把图灵手臂的 VLA 数据管线（`pick_place` 场景）迁到本工程的 `Gripper` 后，做一个「低置信度时由 VLA 兜底」的抓取分支；
- **感知升级**：用本机 YOLO 训练瓶装水/托盘检测，替换 `MockVision`；
- **导航升级**：接入官方 SLAM 或视觉里程计，`_nav` 不变。

---

## 9. 已知边界

- 官方 **评分细则与 SDK 接口尚未公布**，`任务五/六` 的量化条件按「稳定性 + 操作规范」做了合理假设，已在文档中标注；
- 仿真为**离散事件近似**，不替代真机标定；上机前必须做真实坐标与夹爪反馈标定；
- 演示默认离线（`voice.backend=mock`），Windows 比赛电脑可切 `sapi`。

---

## 许可

MIT，见 [`LICENSE`](LICENSE)。第三方资源（LeRobot / XLeRobot / reBot-DevArm / RealFactory-Ego-Data 等）各自遵循其原协议，本仓库不内联其代码。
