"""Small GPU smoke test for a pinned public LeRobot state/action dataset.

This is a data-pipeline/compute check only. It is not an A-track score or
evidence of real-robot task performance.
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=10)
    args = parser.parse_args()

    info = json.loads((args.dataset / "meta" / "info.json").read_text(encoding="utf-8"))
    table = pq.read_table(args.dataset / "data" / "chunk-000" / "file-000.parquet",
                          columns=["observation.state", "action", "episode_index"])
    states = np.asarray(table["observation.state"].combine_chunks().to_pylist(), dtype=np.float32)
    actions = np.asarray(table["action"].combine_chunks().to_pylist(), dtype=np.float32)
    episodes = np.asarray(table["episode_index"].combine_chunks().to_numpy(), dtype=np.int64)
    unique = np.unique(episodes)
    if unique.size < 5 or states.shape != actions.shape:
        raise ValueError(f"Unexpected data dimensions: {states.shape}, {actions.shape}, episodes={unique.size}")

    rng = np.random.default_rng(20261107)
    shuffled = rng.permutation(unique)
    cut = max(1, int(round(len(shuffled) * 0.8)))
    train_eps, val_eps = set(shuffled[:cut]), set(shuffled[cut:])
    train_mask = np.isin(episodes, list(train_eps))
    val_mask = np.isin(episodes, list(val_eps))
    xmean, xstd = states[train_mask].mean(0), states[train_mask].std(0).clip(1e-5)
    ymean, ystd = actions[train_mask].mean(0), actions[train_mask].std(0).clip(1e-5)
    x = (states - xmean) / xstd
    y = (actions - ymean) / ystd

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; refusing to label a CPU run as GPU training")
    if args.gpu < 0 or args.gpu >= torch.cuda.device_count():
        raise ValueError(f"GPU index {args.gpu} not available; count={torch.cuda.device_count()}")
    device = torch.device(f"cuda:{args.gpu}")
    torch.manual_seed(20261107)
    model = nn.Sequential(nn.Linear(states.shape[1], 128), nn.GELU(),
                          nn.Linear(128, 128), nn.GELU(), nn.Linear(128, actions.shape[1])).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    train_ds = TensorDataset(torch.from_numpy(x[train_mask]), torch.from_numpy(y[train_mask]))
    train_loader = DataLoader(train_ds, batch_size=512, shuffle=True, generator=torch.Generator().manual_seed(7))
    val_x = torch.from_numpy(x[val_mask]).to(device)
    val_y = torch.from_numpy(y[val_mask]).to(device)
    criterion = nn.MSELoss()
    start = time.perf_counter()
    history = []
    for epoch in range(args.epochs):
        model.train()
        losses = []
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(bx), by)
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        model.eval()
        with torch.no_grad():
            val_mse = criterion(model(val_x), val_y).item()
        history.append({"epoch": epoch + 1, "train_mse_normalized": float(np.mean(losses)),
                        "heldout_episode_mse_normalized": val_mse})
    torch.cuda.synchronize(device)
    elapsed = time.perf_counter() - start
    result = {
        "purpose": "external_dataset_gpu_pipeline_smoke_test_only",
        "dataset": "lerobot/aloha_mobile_wipe_wine",
        "dataset_revision": "b57bde2a10c343cbc2be9a0052f126854c4bb091",
        "dataset_task": "mobile bimanual wipe wine; not the Pazhou A-track task",
        "robot_type": info["robot_type"], "fps": info["fps"],
        "rows": int(len(states)), "episodes": int(unique.size),
        "train_episodes": sorted(map(int, train_eps)), "validation_episodes": sorted(map(int, val_eps)),
        "input_dim": int(states.shape[1]), "target_dim": int(actions.shape[1]),
        "device": str(device), "gpu_name": torch.cuda.get_device_name(device),
        "torch": torch.__version__, "cuda": torch.version.cuda,
        "python_platform": platform.platform(), "epochs": args.epochs,
        "elapsed_seconds": round(elapsed, 3), "history": history,
        "limitations": ["held-out episode regression is not task success", "no images used",
                        "different robot and task", "not an official competition evaluation"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["device", "gpu_name", "rows", "episodes", "elapsed_seconds"]},
                     ensure_ascii=False))
    print(json.dumps(history[-1], ensure_ascii=False))


if __name__ == "__main__":
    main()
