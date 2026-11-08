path = "/home/nvidia/microduck-course-run/topic/02-可运行代码/microduck-playground-stilts/scripts/audit_motrix_checkpoint.py"
src = open(path, encoding="utf-8").read()
src = src.replace("from motrix_rl.fastsac.networks import Actor",
                  "from motrix_rl_builtin.fastsac.networks import Actor")
src = src.replace("from motrix_rl.fastsac.buffer import EmpiricalNormalization",
                  "from motrix_rl_builtin.fastsac.buffer import EmpiricalNormalization")
open(path, "w", encoding="utf-8").write(src)
print("patched")
