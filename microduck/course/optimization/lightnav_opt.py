#!/usr/bin/env python3
"""LightNav-0 控制层优化实验（不改模型、不把目标真值交给控制器）

诊断依据（原版三场景实测）：
  - MPC 下发命令 v 一直顶格 0.30，但实际路径速度只有 0.155-0.167 m/s（命令的 52-56%）
  - 官方住宅 2.946 m 起点，10.0 s 就 model_stop，只走了 1.06 m
  - seconds 预算 24 s，三场景全部在 10-12.5 s 提前结束，浪费一半以上时间

三个实验臂：
  base   v_max=0.30  stop=model    —— 基线，用于同批次对照
  fast   v_max=0.55  stop=model    —— 只提速，看模型会停在哪
  full   v_max=0.55  stop=ignore   —— 走满时长，给出"停早了值多少"的上界

目标位置只用于事后测量，绝不进入控制回路。
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

LESSON_DIR = Path("/home/nvidia/microduck-course-run/topic/02-可运行代码/lightnav-learning")
sys.path.insert(0, str(LESSON_DIR))

import lightnav_lesson as L  # noqa: E402


def run_episode(scene_id, scene, robot_model, walking_policy, server_url, output,
                seconds=24.0, prediction_period=0.25, fps=10,
                v_max=0.30, stop_mode="model", stop_confirm=2, tag="run", tail_seconds=0.0):
    """与课程原版同构，只把 v_max / 停止策略 / 时长变成参数。"""
    import imageio.v2 as imageio
    import mujoco
    from PIL import Image
    import websocket
    from vln_mujoco.mpc import (MPCController, build_pose_aligned_reference,
                                project_body_to_world, Q_WEIGHTS, R_WEIGHTS)

    output = Path(output) / tag
    output.mkdir(parents=True, exist_ok=True)

    robot = L.make_robot(scene, robot_model, walking_policy)
    renderer = mujoco.Renderer(robot.model, height=270, width=480)
    controller = MPCController(horizon=5, dt_s=0.1, w_max=1.2, a_max_v=2.0, a_max_w=5.0,
                               q_weights=Q_WEIGHTS, r_weights=R_WEIGHTS)
    video_path = output / f"{scene_id}_latest.mp4"
    writer = imageio.get_writer(video_path, fps=fps, codec="libx264", quality=7,
                                macro_block_size=2, ffmpeg_params=["-movflags", "+faststart"])

    connection = None
    predictions, trace = [], []
    termination = "time_limit"
    command = (0.0, 0.0)
    world_path = None
    latest = None
    stop_streak = 0
    tail_until = None
    next_prediction = next_control = next_frame = 0.0
    start_wall = time.monotonic()
    initial = np.asarray(robot.state().pose[:2])
    sequence = 0

    try:
        for _ in range(100):
            robot.step((0.0, 0.0))
        start_time = float(robot.data.time)

        connection = websocket.create_connection(
            server_url, timeout=90, http_no_proxy=["127.0.0.1", "localhost"])
        connection.send(json.dumps({"action": "login",
                                    "data": {"clientId": f"opt-{tag}-{scene_id}"}}))
        login = json.loads(connection.recv())
        if login.get("data", {}).get("rc") != 0:
            raise RuntimeError(f"Model login failed: {login}")

        while float(robot.data.time) - start_time < seconds:
            elapsed = float(robot.data.time) - start_time
            state = robot.state()
            pose = np.array([state.pose[0], state.pose[1], state.pose[3]])

            if elapsed + 1e-8 >= next_prediction:
                rgb = L.camera_image(robot, renderer)
                jpeg = io.BytesIO()
                Image.fromarray(rgb).save(jpeg, format="JPEG", quality=90)
                sequence += 1
                sent = time.monotonic()
                connection.send(json.dumps({"action": "next", "data": {
                    "seq": sequence,
                    "image": base64.b64encode(jpeg.getvalue()).decode("ascii"),
                    "instruction": scene["instruction"]}}))
                latest, body_path = L.decode_response(connection.recv(), sequence)
                latency = 1000 * (time.monotonic() - sent)
                world_path = project_body_to_world(body_path, pose)
                predictions.append({"sim_time": round(elapsed, 3), "latency_ms": latency,
                                    "pose": pose.tolist(), "v_cmd": command[0], **latest})
                next_prediction += prediction_period

                if latest["stop"]:
                    stop_streak += 1
                else:
                    stop_streak = 0

                do_stop = False
                if stop_mode == "model":
                    do_stop = bool(latest["stop"])
                elif stop_mode == "confirm":
                    do_stop = stop_streak >= stop_confirm
                elif stop_mode == "ignore":
                    do_stop = False
                elif stop_mode == "tail":
                    do_stop = bool(latest["stop"])
                else:
                    raise ValueError(f"unknown stop_mode {stop_mode}")

                if do_stop:
                    if stop_mode == "tail" and tail_seconds > 0:
                        # 模型已判定到点，但它给出的那条轨迹还没走完。
                        # 只把模型自己预测的这段走完，不追问模型、不改目标。
                        tail_until = elapsed + tail_seconds
                        termination = "model_stop_tail"
                        next_prediction = float("inf")
                        print(f"[tail] stop at {elapsed:.2f}s, continue tracking "
                              f"{tail_seconds}s of the model's own last trajectory", flush=True)
                    else:
                        command = (0.0, 0.0)
                        termination = "model_stop"
                        writer.append_data(L._annotated_frame(robot, renderer, scene_id, elapsed, latest))
                        break

            if elapsed + 1e-8 >= next_control and world_path is not None:
                reference = build_pose_aligned_reference(world_path, pose, horizon=5, weights=Q_WEIGHTS)
                command, _ = controller.solve(pose, reference, command, v_max=v_max)
                next_control += 0.1

            if elapsed + 1e-8 >= next_frame:
                writer.append_data(L._annotated_frame(robot, renderer, scene_id, elapsed, latest))
                trace.append({"sim_time": elapsed, "x": state.pose[0], "y": state.pose[1],
                              "z": state.pose[2], "v": command[0], "yaw_rate": command[1]})
                next_frame += 1 / fps

            if state.pose[2] < 0.065 or not np.isfinite(robot.data.qpos).all():
                termination = "fall"
                break

            if tail_until is not None and elapsed >= tail_until:
                break

            robot.step(command)

        for step in range(200):
            robot.step((0.0, 0.0))
            if step % 20 == 0:
                writer.append_data(L._annotated_frame(
                    robot, renderer, scene_id, robot.data.time - start_time, latest))
    finally:
        if connection is not None:
            connection.close()
        writer.close()
        renderer.close()

    if not predictions:
        raise RuntimeError("No real model prediction was recorded")

    final = robot.state().pose
    target = np.asarray(scene["target_xy"])
    pts = [(t["x"], t["y"]) for t in trace]
    path_len = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) if len(pts) > 1 else 0.0
    straight = math.dist(pts[0], pts[-1]) if len(pts) > 1 else 0.0
    duration = float(robot.data.time) - start_time
    vs = [t["v"] for t in trace]

    report = {
        "scene": scene_id, "arm": tag,
        "instruction": scene["instruction"],
        "v_max": v_max, "stop_mode": stop_mode, "stop_confirm": stop_confirm,
        "tail_seconds": tail_seconds,
        "seconds_budget": seconds,
        "prediction_count": len(predictions),
        "termination": termination,
        "sim_seconds": duration,
        "wall_seconds": time.monotonic() - start_wall,
        "median_latency_ms": float(np.median([p["latency_ms"] for p in predictions])),
        "initial_target_distance_m": float(np.linalg.norm(initial - target)),
        "final_target_distance_m": float(np.linalg.norm(np.array(final[:2]) - target)),
        "final_trunk_height_m": float(final[2]),
        "path_length_m": float(path_len),
        "straight_displacement_m": float(straight),
        "path_efficiency": float(straight / path_len) if path_len > 0 else 0.0,
        "actual_path_speed_mps": float(path_len / duration) if duration > 0 else 0.0,
        "mean_v_cmd": float(np.mean(vs)) if vs else 0.0,
        "max_v_cmd": float(np.max(vs)) if vs else 0.0,
        "progress_m": float(np.linalg.norm(initial - target) - np.linalg.norm(np.array(final[:2]) - target)),
        "video": str(video_path),
    }
    (output / f"{scene_id}_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / f"{scene_id}_predictions.json").write_text(json.dumps(predictions, indent=2), encoding="utf-8")
    (output / f"{scene_id}_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return report


def apply_command_shape(cmd_max=None, cmd_min=None, deadband=None):
    """放宽上游的命令二值化限制。

    上游 microduck.py 的 shape_microduck_command() 把线性命令压成两档：
      0.08 以下 -> 0；0.08~0.28 -> 直接抬到 0.28；0.30 以上 -> 裁到 0.30。
    结果是机器人只有"停"和"0.28~0.30"两种速度，MPC 无法做中间速度微调，
    窄空间里只能走走停停，直接造成绕路。
    这里只改模块级常量，不动上游文件，保证可复现。
    """
    from vln_mujoco.robots import microduck as md

    before = dict(MAX_LINEAR_COMMAND=md.MAX_LINEAR_COMMAND,
                  MIN_LINEAR_COMMAND=md.MIN_LINEAR_COMMAND,
                  LINEAR_DEADBAND=md.LINEAR_DEADBAND)
    if cmd_max is not None:
        md.MAX_LINEAR_COMMAND = float(cmd_max)
    if cmd_min is not None:
        md.MIN_LINEAR_COMMAND = float(cmd_min)
    if deadband is not None:
        md.LINEAR_DEADBAND = float(deadband)
    after = dict(MAX_LINEAR_COMMAND=md.MAX_LINEAR_COMMAND,
                 MIN_LINEAR_COMMAND=md.MIN_LINEAR_COMMAND,
                 LINEAR_DEADBAND=md.LINEAR_DEADBAND)
    return before, after


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="official_apartment")
    ap.add_argument("--arm", default="base",
                    choices=["base", "fast", "full", "confirm", "tail", "smooth", "smooth_plus", "full_smooth"])
    ap.add_argument("--seconds", type=float, default=24.0)
    ap.add_argument("--tail", type=float, default=6.0, help="tail 臂在 model_stop 后继续跟踪的秒数")
    ap.add_argument("--port", type=int, default=8050)
    ap.add_argument("--out", default="/home/nvidia/microduck-course-run/recordings/lightnav_opt")
    args = ap.parse_args()

    robot_model = Path("/home/nvidia/workspaces/microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml")
    walking_policy = Path("/home/nvidia/microduck-course-run/checkpoints/microduck-navigation/alpha_walking.onnx")
    model_env = Path("/home/nvidia/microduck-course-run/envs/lightnav-0")
    model_path = Path("/home/nvidia/microduck-course-run/checkpoints/LightNav-0")

    out = Path(args.out)
    server = L.ensure_model_server(model_env, model_path, out, port=args.port, timeout=600)
    print(f"[server] {server}", flush=True)

    scenes = L.build_scenes(out / "scenes")
    if args.scene not in scenes:
        raise SystemExit(f"unknown scene {args.scene}; have {list(scenes)}")

    configs = {
        "base":        dict(v_max=0.30, stop_mode="model"),
        "fast":        dict(v_max=0.55, stop_mode="model"),
        "full":        dict(v_max=0.55, stop_mode="ignore"),
        "confirm":     dict(v_max=0.55, stop_mode="confirm", stop_confirm=2),
        "tail":        dict(v_max=0.30, stop_mode="tail", tail_seconds=args.tail),
        "smooth":      dict(v_max=0.30, stop_mode="model"),
        "smooth_plus": dict(v_max=0.40, stop_mode="model"),
        "full_smooth": dict(v_max=0.40, stop_mode="ignore"),
    }
    cfg = configs[args.arm]

    # 命令整形参数：(MAX, MIN, DEADBAND)，None 表示保持上游值
    shape = {
        "smooth":      (None, 0.10, 0.03),
        "smooth_plus": (0.40, 0.10, 0.03),
        "full_smooth": (0.40, 0.10, 0.03),
    }
    if args.arm in shape:
        before, after = apply_command_shape(*shape[args.arm])
        print(f"[shape] {before} -> {after}", flush=True)

    print(f"[start] {args.scene} / {args.arm} / {cfg} / seconds={args.seconds}", flush=True)
    report = run_episode(args.scene, scenes[args.scene], robot_model, walking_policy,
                         server["url"], out, seconds=args.seconds, tag=args.arm, **cfg)
    if args.arm in shape:
        report["command_shape"] = after
    (out / args.arm / f"{args.scene}_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
