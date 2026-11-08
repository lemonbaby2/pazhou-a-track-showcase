#!/usr/bin/env python3
"""MotrixLab scripts/export_onnx.py shim.

The 03-Notebook curriculum expects ``scripts/export_onnx.py run_dir=<dir>
output=<onnx> opset=11``. The real Hydra entry point is
``motrix_rl.commands.export_onnx`` (``mxlab export-onnx``) and accepts the
same overrides, so forward argv verbatim.
"""
from __future__ import annotations

import sys


def main() -> None:
    sys.argv = ["mxlab export-onnx", *sys.argv[1:]]
    from motrix_rl.commands.export_onnx import main as export_main

    export_main()


if __name__ == "__main__":
    main()
