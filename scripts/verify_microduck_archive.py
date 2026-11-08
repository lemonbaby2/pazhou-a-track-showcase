"""归档自检：HTML/Markdown 本地引用、站点资产体积、清单一致性。

用法：python scripts/verify_microduck_archive.py
退出码非 0 表示有死链或超限文件。
"""
from __future__ import annotations

import csv
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
MOD = ROOT / "microduck"
SKIP = ("http:", "https:", "mailto:", "data:", "#")


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.refs.append(v)


def check_html(path: Path, base: Path) -> list[str]:
    p = Refs()
    p.feed(path.read_text(encoding="utf-8"))
    missing = []
    for ref in p.refs:
        if ref.startswith(SKIP):
            continue
        target = base / ref.split("#", 1)[0]
        if not target.exists():
            missing.append(f"{path.name}: {ref}")
    return missing, len(p.refs)


MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def check_md(path: Path) -> list[str]:
    missing = []
    for raw in MD_LINK.findall(path.read_text(encoding="utf-8")):
        ref = raw.strip().split()[0] if raw.strip() else ""
        if not ref or ref.startswith(SKIP):
            continue
        target = (path.parent / ref.split("#", 1)[0]).resolve()
        if not target.exists():
            missing.append(f"{path.relative_to(ROOT)}: {ref}")
    return missing


problems: list[str] = []
html_stats = []
for name in ["index.html", "microduck.html"]:
    miss, n = check_html(SITE / name, SITE)
    html_stats.append(f"{name}: {n} refs, {len(miss)} missing")
    problems += miss

md_files = [
    ROOT / "README.md",
    ROOT / "site" / "README.md",
    MOD / "README.md",
    MOD / "METRICS.md",
    MOD / "RECOMMENDATIONS.md",
    MOD / "README_sprint.md",
    MOD / "course" / "README.md",
    MOD / "course" / "optimization" / "README.md",
    MOD / "papers" / "README.md",
    MOD / "docs" / "HARDWARE_BOM.md",
    MOD / "docs" / "METRICS_PROTOCOL.md",
]
for f in md_files:
    if f.exists():
        problems += check_md(f)

# 站点单文件 5 MiB 限制（与 scripts/verify_public_package.py 一致）
oversize = [(str(p.relative_to(SITE)), p.stat().st_size)
            for p in SITE.rglob("*") if p.is_file() and p.stat().st_size > 5 * 1024 * 1024]

# MANIFEST 与磁盘一致性
rows = list(csv.DictReader((MOD / "MANIFEST.csv").open(encoding="utf-8-sig")))
manifest_paths = {r["path"] for r in rows}
disk_paths = {p.relative_to(MOD).as_posix()
              for p in MOD.rglob("*") if p.is_file() and p.name != "MANIFEST.csv"}
missing_in_manifest = disk_paths - manifest_paths
stale_in_manifest = manifest_paths - disk_paths

print("HTML:", "; ".join(html_stats))
print(f"Markdown 文件检查: {len([f for f in md_files if f.exists()])} 份")
print(f"MANIFEST: {len(rows)} 条 / 磁盘 {len(disk_paths)} 文件")
print(f"  MANIFEST 漏记: {len(missing_in_manifest)}  过期条目: {len(stale_in_manifest)}")
print(f"site/ >5MiB 文件: {len(oversize)}")
print(f"本地死链合计: {len(problems)}")
for p in problems[:40]:
    print("  MISSING", p)
for p in list(missing_in_manifest)[:10]:
    print("  NOT_IN_MANIFEST", p)
for p in list(stale_in_manifest)[:10]:
    print("  STALE", p)

if problems or oversize or missing_in_manifest or stale_in_manifest:
    raise SystemExit(1)
print("ARCHIVE OK")
