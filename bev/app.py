"""统一入口。

- ``python -m bev.app``        走仿真后端（本机可直接跑）
- ``python -m bev.app --real`` 走官方 SDK 适配器（需先填 bev/adapters/vendor_sdk.py）
"""

from __future__ import annotations

import sys


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--real" in argv:
        raise SystemExit(
            "官方 SDK 尚未接入。请先在 bev/adapters/vendor_sdk.py 填好 5 个接口，"
            "然后在此处调用 build_robot_io(sdk) 并交给 BeverageTask。"
        )
    # 去掉 --real 以外的参数直接透传给仿真入口
    from sim.run_sim import main as sim_main

    return sim_main([a for a in argv if a != "--sim"])


if __name__ == "__main__":
    raise SystemExit(main())
