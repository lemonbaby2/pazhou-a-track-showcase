import sys
import onnxruntime as ort

paths = sys.argv[1:]
for p in paths:
    print("==", p)
    try:
        s = ort.InferenceSession(p, providers=["CPUExecutionProvider"])
    except Exception as exc:
        print("  FAIL", type(exc).__name__, str(exc)[:200])
        continue
    print("  INPUTS")
    for i in s.get_inputs():
        print("   ", i.name, i.shape, i.type)
    print("  OUTPUTS")
    for o in s.get_outputs():
        print("   ", o.name, o.shape, o.type)
