import json
import glob

SITE = r"C:\Users\lzp\Documents\xwechat_files\wxid_zmxb0wapngqm22_00d0\msg\file\2026-10\microduck-task2\datawhale_microduck"
records = []
for f in sorted(glob.glob(SITE + r"\logs\0*_execution.json")):
    records.append(json.load(open(f, encoding="utf-8")))
master = {
    "generated_at": "2026-10-21",
    "round": 2,
    "environment": "NVIDIA DGX Spark (GB10, aarch64, sm_121), CUDA 13.0",
    "summary": {
        "total": len(records),
        "executed": sum(1 for r in records if r["status"] == "executed"),
        "failed": sum(1 for r in records if r["status"] == "failed"),
    },
    "tasks": records,
}
out = SITE + r"\logs\run_all_master.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(master, f, ensure_ascii=False, indent=1)
print("master written:", master["summary"])
