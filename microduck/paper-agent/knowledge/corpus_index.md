# 本机可参考论文与资料索引

写作前按主题取读。路径为本机实际存在的位置。

## 一、本项目论文谱系（最优先）

| 路径 | 内容 |
|---|---|
| `E:\VLA_SOP_论文归档_20261018\01_VLA具身机器人_论文\TAC-R2S2R投稿稿\2026.10.12_TAC-R2S2R具身操作算法改进投稿稿(1).docx` | 上一版投稿稿 |
| `E:\VLA_SOP_论文归档_20261018\01_VLA具身机器人_论文\Real2Sim2Real论文_版本谱系\10.10(4)_期刊投稿版.docx` | 更早的 Real2Sim2Real 版本 |
| `E:\VLA_SOP_论文归档_20261018\01_VLA具身机器人_论文\审稿与修改建议\面向机器人操作Real2Sim2Real论文_完整识别分析与审稿建议.docx` | 审稿意见，修改依据 |
| `E:\VLA_SOP_论文归档_20261018\01_VLA具身机器人_论文\开放论文合集\VLA_Competition_10_OpenAccess_Papers_Pack.zip` | 10 篇开放获取 VLA 论文包 |
| 本次源稿：`论文2026.10.29TAC-R2S2R_导师意见修订稿.docx` | 已抽取为 `source_TAC-R2S2R.txt` |

## 二、VLA / 具身方向

- `D:\具身智能的北理工\papers\arxiv_2210.03629.pdf`（ReAct）
- `D:\具身智能的北理工\papers\arxiv_2305.10601.pdf`（Tree of Thoughts）
- `D:\具身智能的北理工\LingBot-VLA_训练与真机部署手册.md`
- `E:\AI_GLASSES_OSINT_20261005\06_papers\`：Qwen2.5-VL / Qwen2.5-Omni / Qwen3-VL / Qwen3-Omni 技术报告，
  用于多模态表述与图表风格参考
- `E:\VLA_SOP_论文归档_20261018\04_VLA具身机器人_行业报告与公司资料\`：行业背景数据

## 三、实验写作范式参考（CV 方向，结构可借鉴）

`D:\手提研一广工研究生研究生论文\3D检测论文\` 下的 CVPR/ECCV 论文：
PointNet、PointNet++、PointPillars、PointRCNN、CIA-SSD、CLOCs、EPNet 等。
重点看它们的**实验章组织方式**：数据集 → 指标 → 主表 → 消融 → 可视化 → 失败案例。

## 四、方法引用（论文参考文献实际使用）

RT-1 / RT-2 / OpenVLA / Octo / π0 / Domain Randomization / Dynamics Randomization /
SimOpt / BayesSim / PPO / MuJoCo / Rudin 并行 RL / Hwangbo ANYmal / RMA / Orbit(Isaac Lab) /
Open X-Embodiment / Pollen MicroDuck。
均为真实公开文献，引用格式见 `build_paper.py` 末尾。

## 五、使用建议

- 写"相关工作"先读第一节的审稿意见，避免重复被批的问题；
- 写"实验"参照第三节 CVPR 论文的四层结构（总体 / 偏移 / 消融 / 失败）；
- 所有性能数字只从 `data/*.json` 取，不从记忆或他人论文搬。
