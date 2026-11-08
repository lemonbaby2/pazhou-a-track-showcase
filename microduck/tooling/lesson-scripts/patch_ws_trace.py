import json

path = "/home/nvidia/microduck-course-run/topic/03-Notebook/08_LightNav0_视觉语言导航_GPU_多场景.ipynb"
nb = json.load(open(path, encoding="utf-8"))
c = nb["cells"][11]
lines = c["source"]
out = []
inserted = False
for line in lines:
    out.append(line)
    if not inserted and line.strip() == "import websocket":
        out.append("websocket.enableTrace(True)\n")
        inserted = True
assert inserted, "import websocket line not found"
c["source"] = out
with open(path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("trace enabled")
