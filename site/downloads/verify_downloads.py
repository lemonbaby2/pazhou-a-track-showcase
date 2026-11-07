from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
import imageio_ffmpeg
import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
summary = {"datasets": []}
for name in ("aloha_mobile_wipe_wine", "aloha_static_coffee"):
    base = ROOT / name
    manifest = json.loads((ROOT / f"{name}_manifest.json").read_text(encoding="utf-8"))
    hash_ok = []
    for item in manifest["files"]:
        path = ROOT / item["path"]
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
                h.update(block)
        hash_ok.append(h.hexdigest() == item["sha256"] and path.stat().st_size == item["bytes"])
    info = json.loads((base / "meta/info.json").read_text(encoding="utf-8"))
    data = pq.read_table(base / "data/chunk-000/file-000.parquet",
                         columns=["observation.state", "action", "episode_index", "timestamp"])
    states = np.asarray(data["observation.state"].combine_chunks().to_pylist(), dtype=np.float32)
    actions = np.asarray(data["action"].combine_chunks().to_pylist(), dtype=np.float32)
    episode = np.asarray(data["episode_index"].combine_chunks().to_numpy(), dtype=np.int64)
    timestamp = np.asarray(data["timestamp"].combine_chunks().to_numpy(), dtype=np.float64)
    episode_table = pq.read_table(base / "meta/episodes/chunk-000/file-000.parquet")
    epdf = episode_table.to_pydict()
    episode_lengths = epdf.get("length", [])
    decode_checks = []
    for p in sorted((base / "videos").glob("**/*.mp4")):
        proc = subprocess.run([ffmpeg, "-v", "error", "-i", str(p), "-t", "2", "-f", "null", "-"],
                              capture_output=True, text=True, timeout=120)
        decode_checks.append({"file": str(p.relative_to(base)), "first_two_seconds_decoded": proc.returncode == 0,
                              "stderr": proc.stderr[:300]})
    ts_monotonic = all(np.all(np.diff(timestamp[episode == e]) > 0) for e in np.unique(episode))
    item = {
        "name": name, "revision": manifest["revision"], "manifest_files": len(manifest["files"]),
        "manifest_hash_and_size_all_match": all(hash_ok), "rows": int(data.num_rows),
        "metadata_rows": int(info["total_frames"]), "episode_count": int(np.unique(episode).size),
        "metadata_episode_count": int(info["total_episodes"]),
        "episode_lengths_min": int(min(episode_lengths)), "episode_lengths_max": int(max(episode_lengths)),
        "state_shape": list(states.shape), "action_shape": list(actions.shape),
        "finite_state_action": bool(np.isfinite(states).all() and np.isfinite(actions).all()),
        "timestamp_strictly_monotonic_per_episode": bool(ts_monotonic),
        "video_count": len(decode_checks), "video_decode_checks": decode_checks,
    }
    summary["datasets"].append(item)
out = ROOT / "dataset_qc_report.json"
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
if any(not d["manifest_hash_and_size_all_match"] or d["rows"] != d["metadata_rows"] or
       d["episode_count"] != d["metadata_episode_count"] or not d["finite_state_action"] or
       not d["timestamp_strictly_monotonic_per_episode"] or
       any(not v["first_two_seconds_decoded"] for v in d["video_decode_checks"]) for d in summary["datasets"]):
    raise SystemExit("QC_FAILED")
