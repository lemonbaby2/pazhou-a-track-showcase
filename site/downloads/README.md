# A 赛道参考数据包（2026-11-07）

数据下载后可放在任意本地目录；本仓库只保存来源、固定 revision、哈希清单和下载/质检脚本，不保存原始大体积视频。

## 已下载数据

| Dataset | 固定 revision | 文件数 | 大小 | 用途 |
|---|---|---:|---:|---|
| `aloha_mobile_wipe_wine/` | `b57bde2a10c343cbc2be9a0052f126854c4bb091` | 11 | 1,298,533,975 bytes | 移动双臂桌面清理演示 |
| `aloha_static_coffee/` | `b144896feb1f37398a862927b22cd3abdf005a6b` | 11 | 1,566,268,108 bytes | 静态双臂咖啡操作演示 |

两份数据页分别标注 MIT 许可证；使用或重新分发前仍须保留来源与许可证信息。它们不包含琶洲 A 赛道完整任务示范。

## 核验和 GPU 运行

`*_manifest.json` 记录每个下载文件的 SHA-256 与大小。完整核验报告为 `dataset_qc_report.json`。复核命令：

```bash
python verify_downloads.py
```

在 RTX 5060 Ti 上完成的 10 epoch 状态到动作回归管线检查输出为 `gpu_probe_mobile_wipe_wine.json`。重新运行：

```bash
python ../scripts/train_external_dataset_probe.py \
  --dataset /path/to/aloha_mobile_wipe_wine \
  --output ./gpu_probe_mobile_wipe_wine.json --gpu 0 --epochs 10
```

请注意：GPU 脚本是外部数据管线冒烟测试，不是视觉模型，也不代表官方比赛成绩或真机性能。
