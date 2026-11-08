#!/usr/bin/env python3
"""MotrixLab scripts/train.py shim.

The 03-Notebook curriculum expects ``scripts/train.py`` inside MotrixLab.
The source tree ships the real entry point as the ``mxlab train`` CLI
(``motrix_rl.commands.train``); this shim forwards argv so notebook cells
keep working unchanged.
"""
from __future__ import annotations

import sys


def main() -> None:
    sys.argv = ["mxlab train", *sys.argv[1:]]
    from motrix_rl.commands.train import main as train_main

    train_main()


if __name__ == "__main__":
    main()
