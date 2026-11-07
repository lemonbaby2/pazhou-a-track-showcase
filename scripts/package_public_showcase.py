from __future__ import annotations
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "pazhou_a_public_showcase_2026-11-07.zip"
include = [ROOT / "site", ROOT / "wrangler.jsonc",
           ROOT / "scripts/build_public_video.py", ROOT / "scripts/create_video_narration.ps1",
           ROOT / "scripts/verify_public_package.py", ROOT / "scripts/package_public_showcase.py",
           ROOT / "docs/开源真机数据与赛题适配_20261107.md",
           ROOT / "docs/赛题本地规则测试记录_20261107.md"]
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for item in include:
        if item.is_dir():
            for path in item.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(ROOT))
        else:
            zf.write(item, item.relative_to(ROOT))
with zipfile.ZipFile(OUT) as zf:
    bad = zf.testzip()
    if bad:
        raise SystemExit(f"Archive CRC failure: {bad}")
print({"archive": str(OUT), "bytes": OUT.stat().st_size, "files": len(zf.namelist())})
