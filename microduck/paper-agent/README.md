# paper-agent —— 会写论文的鳌虾分身

不是"训练一个写作模型"，而是**知识库 + 真实实验数据 + 可复现的生成脚本**。
所有数字都来自 DGX 的真实训练日志，脚本可一键重跑，论文随实验推进自动更新。

## 目录

```
paper-agent/
├── README.md                      本文件
├── knowledge/
│   ├── source_TAC-R2S2R.txt        原论文全文（195 段 + 8 表，导师意见修订稿）
│   ├── style_guide.md             写作规范（结构 / 语气 / 图表 / 证据口径）
│   ├── experiment_log.md          MicroDuck 实验事实档案（可追溯）
│   └── corpus_index.md            本机可参考论文与资料索引
├── data/                          真实实验数据（JSON）
│   ├── v1_metrics.json            Sprint v1 训练曲线（888 迭代）
│   ├── v1_speed.json              v1 实测前进速度
│   ├── v2_metrics.json            Sprint v2 训练曲线（随训练更新）
│   └── v2_speed.json              v2 实测前进速度
├── figs/                          论文插图（make_figs.py 生成）
├── make_figs.py                   数据 → 图
├── build_paper.py                 数据 + 图 → 双栏 docx
└── MicroDuck短跑策略_Real2Sim2Real_双栏投稿稿.docx
```

## 一次完整重跑

```bash
# 1. DGX 侧导出训练曲线
ssh nvidia@192.168.1.217 'cd ~/duck-rl && .venv/bin/python export_sprint_metrics.py \
    logs/rsl_rl/velocity/<run_dir> -o logs/v2_metrics.json'

# 2. DGX 侧实测速度（独立进程，不依赖训练统计）
ssh nvidia@192.168.1.217 'cd ~/duck-rl && .venv/bin/python probe_sprint_speed.py \
    --ckpt logs/rsl_rl/velocity/<run_dir>/model_750.pt --cmd 2.6 \
    --steps 1000 --num-envs 32 -o logs/v2_speed.json'

# 3. 拉回本地
scp nvidia@192.168.1.217:~/duck-rl/logs/v2_metrics.json paper-agent/data/
scp nvidia@192.168.1.217:~/duck-rl/logs/v2_speed.json   paper-agent/data/

# 4. 生成图与论文
cd paper-agent && python make_figs.py && python build_paper.py
```

## 铁律（写论文时不可违反）

1. **没有实测数字就不写性能结论。** 预期收益、计划值、他人论文数字都不能写成本文结果。
2. **回合奖励 ≠ 性能。** 本文唯一性能判据是独立进程测出的前进速度。
3. **失败必须归因到类型**（几何 / 物理 / 语义 / 策略—目标），不能一律叫"域偏移"。
4. **改动必须可追溯**：每一版配方对应一个任务名、一份日志、一组检查点。
