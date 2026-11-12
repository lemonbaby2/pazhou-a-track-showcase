# π0.5 3.6B · 8 小时连续训练 · 全量归档

> **状态：已完成。** 编排器于 `2026-11-11 20:23:14` 结束（`state/status.json` → `phase: done`），
> 4 个消融臂全部跑完；GPU 已空闲，监控进程仍在每 5 分钟采集快照。
> 本目录是 DGX `spark-a8d2` 上 `/home/nvidia/vla-8h/` 的**逐字节镜像**（不含模型权重与 checkpoint）。

- **实时看板**：<https://lemonbaby2.github.io/pazhou-a-track-showcase/vla-8h.html>（页面 5 分钟自动刷新）
- **站点首页**：<https://lemonbaby2.github.io/pazhou-a-track-showcase/>
- **归档时间**：2026-11-12 15:0x（GMT+8），共 20 个文件 / 1,471,374 B
- **数据来源**：`nvidia@192.168.1.217:/home/nvidia/vla-8h/`，SFTP 只读拉取，未改动 DGX 任何进程或配置

---

## 1. 结论：4 个消融臂结果

模型 π0.5 3.6B（`pi05_base`），数据集 LIBERO v3.0，DGX Spark GB10 单卡 BF16，
实测冒烟速度 **0.6433 step/s**，每臂计划 **4015 步**，总预算 8 小时（含 30 min 冒烟）。

| 臂 | 自变量 | 终止码 | loss 首 | loss 末 | loss 最小 | 采样点 | 完成步数 | 判定 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `A_ki` | 基线：Knowledge Insulation + QUANTILES + Beta(1.5,1.0) | 0 | 0.4630 | 0.2100 | 0.2030 | 80 | 4015 | 完整 |
| `B_lm` | 解冻 VLM 语言模型（仅冻结视觉塔） | **124** | 0.4540 | 0.1670 | 0.1640 | 59 | **2974 / 4015** | **超时截断** |
| `C_mstd` | QUANTILES → MEAN_STD | 0 | 0.8600 | 0.4200 | 0.3920 | 80 | 4015 | 完整 |
| `D_beta` | Beta(1.5,1.0) → Beta(1.0,1.0) 均匀时间采样 | 0 | 0.4490 | 0.2240 | 0.2140 | 80 | 4015 | 完整 |

> **读表注意**：四个臂的 loss 绝对值**不可横向比较绝对值大小**──起始 loss 不同（C_mstd 从 0.86 起），
> 只看各自收敛斜率与同臂内的首末差。`B_lm` 的 `rc=124` 是 `timeout` 终止码，
> 不是训练崩溃：它已跑到 2974 步、loss 降到 0.164，是**被 112 分钟时间预算切断**，
> 该臂数据只能作趋势参考，不能与 4015 步的三臂等量对比。

**系统侧（最后一次巡检）**：可用内存 105,673 MB，nuclio 健康 4/4，CVAT 容器 19 个 Up，告警 0，GPU 利用率 0%。

---

## 2. 目录结构

```
vla-8h/
├── README.md                 本文件（索引 + 结论 + 复现说明）
├── reports/
│   ├── PROTOCOL.md           实验协议：自变量设计、已复现项、明确未复现项、生产保护
│   ├── FINAL.md              编排器自动生成的最终汇总表
│   ├── latest.json           最新一次 5 分钟快照
│   ├── latest.md             快照的可读版
│   └── metrics.jsonl         逐条时序指标（83 KB，loss / lr / grad norm / 系统状态）
├── state/
│   ├── results.json          4 臂完整结果，含每臂实际启动命令与终止码
│   └── status.json           编排器状态机（phase / finished_at）
├── figs/
│   └── loss_latest.svg       最后一次 loss 曲线
├── logs/                     原始训练日志（数据真实性凭证，勿改）
│   ├── train_smoke.log       30 分钟冒烟
│   ├── train_A_ki.log  train_B_lm.log  train_C_mstd.log  train_D_beta.log
│   ├── orchestrator.log  monitor.log  download.log  tokenizer.log
├── start_all.sh              DGX 侧脱离 SSH 启动编排器 + 监控
├── status.sh                 DGX 侧状态查询
└── restart_monitor.sh        仅重启监控（不影响训练）
```

配套代码在仓库根目录，**已与 DGX 上的运行版本逐字节比对一致（MD5 相同）**：

| 本地 | DGX 对应 | 作用 |
|---|---|---|
| [`scripts/vla8h_orchestrator.py`](../scripts/vla8h_orchestrator.py) | `~/vla-8h/vla8h.py` | 编排器：等权重 → 冒烟 → 4 臂 → 终稿 |
| [`scripts/vla8h_dashboard.py`](../scripts/vla8h_dashboard.py) | 本机 `C:/Users/lzp/duck-opt/push_report.py` | 拉快照 → 生成 `site/vla-8h.html` → 推 GitHub |

---

## 3. 看板怎么更新（完整启动链路）

整点定时巡检会执行下面这条命令，链路是**全自动**的：

```bash
C:/Users/lzp/.workbuddy/binaries/python/versions/3.13.12/python.exe \
    C:/Users/lzp/duck-opt/push_report.py
```

链路：SSH 读 `latest.json` / `status.json` / `loss_latest.svg`
→ 生成 `site/vla-8h.html` → `git commit` → `git push` 到 `main`
→ 触发 [`.github/workflows/pages.yml`](../.github/workflows/pages.yml) 部署到 GitHub Pages。

脚本会输出一行 JSON 摘要（阶段、臂、loss、采样点、内存、nuclio、告警、`pushed`、URL），
供巡检简报直接引用。推送走 `ssh.github.com:443`（本机 22 端口常超时），失败回退 22。

**手动验证 Pages 是否通**（绕开浏览器代理，直连）：

```bash
curl --noproxy '*' -I https://lemonbaby2.github.io/pazhou-a-track-showcase/vla-8h.html
# 期望 HTTP/1.1 200 OK
```

> 若浏览器打不开但上面这条返回 200，问题在本机浏览器代理，不在服务端。
> 处置顺序：① 重启 Chrome（清掉缓存的死代理）→ ② 用临时 profile 验证
> `chrome.exe --user-data-dir=C:\Temp\chrome-probe <URL>` → ③ 检查扩展/策略是否强制走已失效的本地代理端口。
> 本机代理端口会变（历史 `12002 → 7890 → 7891`），不要写死。

---

## 4. 复现边界（不得模糊）

8 小时只做**少步数微调**，**不复现论文榜单数值**。明确未复现：

| 项 | 原因 |
|---|---|
| π0.5 第一阶段 FAST 离散动作预训练 | 开源仓库只放第二阶段 flow matching head |
| 部署期高层子任务推理 | 开源仓库未包含 |
| 60k steps × global batch 384 全量配方 | DGX Spark 单卡约 21.5 TFLOPS，与 6×A800 差约 90× |
| 原榜单 LIBERO / RoboTwin 数值 | SAPIEN 3.0 仅 x86_64 wheel，aarch64 无法闭环评测 |
| 6B LingBot-VLA / 4B Kairos 全参训练 | 算力不足，仅推理级 |

**数据真实性**：loss / grad norm / lr / step time 全部从 `lerobot_train` 的 tqdm 日志正则解析，
未插值、未伪造；原始日志与 `metrics.jsonl` 均在本目录，可逐条复核。

**生产保护**：训练进程 `nice -n 10` + `taskset -c 0-9`（20 核留一半给产线）；
监控每 5 分钟检查内存与 CVAT / nuclio 健康，可用内存低于 11 GB 时主动终止训练，
保住 CVAT 标注与 4 个 YOLO 推理函数。

---

## 5. 归档范围声明

- 本目录**不含**模型权重、checkpoint、LIBERO 数据集（体积过大，留在 DGX `/home/nvidia/`）。
- 这是独立于 A 赛道赛题的**具身智能能力储备**，不是比赛策略、不是官方计分结果。
- 归档过程为只读拉取，**未修改或终止 DGX 上任何训练进程、监控进程或配置**。
