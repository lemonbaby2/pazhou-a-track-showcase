"""Run only the course notebook's environment cell and verify the released actor."""

import hashlib
import json
from pathlib import Path

import onnx


ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "Task1_篮球平衡_Notebook.ipynb"
MODEL = ROOT / "artifacts" / "basketball" / "policy.onnx"

notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
assert notebook["cells"][2]["cell_type"] == "code"
try:
    exec("".join(notebook["cells"][2]["source"]), {})
    environment_cell = "pass"
except RuntimeError as exc:
    # The standalone archive does not include the entire Datawhale topic tree.
    if "找不到专题目录" not in str(exc):
        raise
    environment_cell = "not_run: set MICRODUCK_TOPIC_ROOT to the official topic directory"

model = onnx.load(MODEL)
onnx.checker.check_model(model)


def shape(value):
    return [dimension.dim_value or dimension.dim_param for dimension in value.type.tensor_type.shape.dim]


report = {
    "source_notebook_cell": 2,
    "environment_cell": environment_cell,
    "notebook_run_all": False,
    "onnx_check": "pass",
    "model_sha256": hashlib.sha256(MODEL.read_bytes()).hexdigest(),
    "inputs": {value.name: shape(value) for value in model.graph.input},
    "outputs": {value.name: shape(value) for value in model.graph.output},
    "nodes": len(model.graph.node),
}
assert report["inputs"]["obs"] == [1, 61]
assert report["outputs"]["actions"] == [1, 14]
print(json.dumps(report, ensure_ascii=False, indent=2))
