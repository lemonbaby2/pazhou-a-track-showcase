import hashlib
import urllib.request
from pathlib import Path

ROOT = Path("/home/nvidia/microduck-course-run/topic/02-可运行代码/MotrixLab")
TARGETS = [
    ROOT / "motrix_robots/src/motrix_robots/assets/microduck",
    ROOT / "motrix_envs/src/motrix_envs/locomotion/ball_balance/assets",
]
BASE = "https://media.githubusercontent.com/media/Motphys/MotrixLab/main/"


def pointer_info(p: Path):
    try:
        head = p.read_bytes()[:200]
    except Exception:
        return None
    if not head.startswith(b"version https://git-lfs.github.com/spec/v1"):
        return None
    text = head.decode("ascii", "replace")
    oid = size = None
    for line in text.splitlines():
        if line.startswith("oid sha256:"):
            oid = line.split("oid sha256:", 1)[1].strip()
        elif line.startswith("size "):
            size = int(line.split("size ", 1)[1].strip())
    return (oid, size) if oid and size else None


fixed = failed = 0
for target in TARGETS:
    if not target.is_dir():
        print("MISSING_DIR", target)
        continue
    for p in sorted(target.rglob("*")):
        if not p.is_file():
            continue
        info = pointer_info(p)
        if not info:
            continue
        oid, size = info
        rel = p.relative_to(ROOT).as_posix()
        try:
            with urllib.request.urlopen(BASE + rel, timeout=180) as r:
                data = r.read()
        except Exception as e:
            print("DOWNLOAD_FAIL", rel, repr(e))
            failed += 1
            continue
        actual = hashlib.sha256(data).hexdigest()
        if actual != oid or len(data) != size:
            print("HASH_MISMATCH", rel, "got", len(data), "want", size)
            failed += 1
            continue
        p.write_bytes(data)
        print("FIXED", rel, len(data))
        fixed += 1
print("fixed=%d failed=%d" % (fixed, failed))
