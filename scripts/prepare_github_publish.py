"""Prepare a clean GitHub publishing tree without inheriting the Gitee remote/history."""
from __future__ import annotations
import argparse
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    target = args.target.resolve()
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty destination: {target}")
    target.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(["git", "-C", str(source), "ls-files", "-z"]).split(b"\0")
    for raw in tracked:
        if not raw:
            continue
        rel = Path(raw.decode("utf-8"))
        src, dst = source / rel, target / rel
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    for rel in [".gitignore", "README.md", ".github", "docs", "scripts", "site", "data_registry", "wrangler.jsonc"]:
        src, dst = source / rel, target / rel
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print(f"Prepared clean publish tree at {target}")


if __name__ == "__main__":
    main()
