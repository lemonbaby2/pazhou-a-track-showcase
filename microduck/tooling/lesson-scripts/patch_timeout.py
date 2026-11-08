import json

BASE = "/home/nvidia/microduck-course-run/topic/03-Notebook/"
for name in ["05_球平衡_FastSAC_ONNX_BPU.ipynb", "06_梯面攀爬_接触与部署模板.ipynb"]:
    path = BASE + name
    nb = json.load(open(path, encoding="utf-8"))
    changed = 0
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        if "timeout=600" in src:
            c["source"] = [line.replace("timeout=600", "timeout=3600") for line in c["source"]]
            changed += 1
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
    print(name, "patched_cells:", changed)
