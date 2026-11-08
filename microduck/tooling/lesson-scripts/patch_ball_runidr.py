import json

path = "/home/nvidia/microduck-course-run/topic/03-Notebook/05_球平衡_FastSAC_ONNX_BPU.ipynb"
nb = json.load(open(path, encoding="utf-8"))
changed = 0
for c in nb["cells"]:
    if c["cell_type"] != "code":
        continue
    src = "".join(c["source"])
    if 'f"run_dir={run_dir}"' in src:
        c["source"] = [line.replace('f"run_dir={run_dir}"', 'f"run_dir=\'{run_dir}\'"') for line in c["source"]]
        changed += 1
if changed:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
print("patched_cells:", changed)
