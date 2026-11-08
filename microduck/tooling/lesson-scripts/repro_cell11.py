import os
import sys
import json
import base64
import io
import traceback

os.environ.setdefault("MUJOCO_GL", "egl")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "4")

TOPIC = "/home/nvidia/microduck-course-run/topic"
LIGHTNAV_ROOT = "/home/nvidia/LightNav-0"
MODEL_ENV = "/home/nvidia/microduck-course-run/envs/lightnav-0"
MODEL_PATH = "/home/nvidia/microduck-course-run/checkpoints/LightNav-0"
ROBOT_MODEL = "/home/nvidia/workspaces/microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml"
WALKING_POLICY = "/home/nvidia/microduck-course-run/checkpoints/microduck-navigation/alpha_walking.onnx"
OUTPUT = "/home/nvidia/microduck-course-run/recordings/lightnav_repro"

import mujoco
import numpy as np
from PIL import Image as PILImage
from IPython.display import display  # noqa

sys.path.insert(0, os.path.join(LIGHTNAV_ROOT, "mujoco_demo"))
sys.path.insert(0, os.path.join(TOPIC, "02-可运行代码/lightnav-learning"))
from lightnav_lesson import ensure_model_server, build_scenes, make_robot, camera_image, decode_response, run_episode  # noqa

os.makedirs(OUTPUT, exist_ok=True)

print("[1] ensure_model_server ...")
service = ensure_model_server(MODEL_ENV, MODEL_PATH, OUTPUT, port=8050)
SERVER_URL = service["url"]
print("service:", service)

print("[2] build_scenes ...")
scenes = build_scenes(os.path.join(OUTPUT, "scenes"))
for name, scene in scenes.items():
    print(name, "|", scene["instruction"])

print("[3] make_robot x3 ...")
robots = {}
for name, scene in scenes.items():
    robot = make_robot(scene, ROBOT_MODEL, WALKING_POLICY)
    robots[name] = robot
    assert robot.model.nu == 14
    assert robot.policy.observation().shape == (61,)
print("robots ok:", list(robots))

print("[4] render living_room ...")
robot = robots["living_room"]
with mujoco.Renderer(robot.model, height=270, width=480) as renderer:
    rgb = camera_image(robot, renderer)
buffer = io.BytesIO()
PILImage.fromarray(rgb).save(buffer, format="JPEG")
print("jpeg bytes:", len(buffer.getvalue()))

print("[5] websocket connect ...")
import websocket
from contextlib import closing
print("SERVER_URL =", SERVER_URL)
with closing(websocket.create_connection(SERVER_URL, timeout=90, http_no_proxy=["127.0.0.1", "localhost"])) as connection:
    connection.send(json.dumps({"action": "login", "data": {"clientId": "repro-test"}}))
    resp = connection.recv()
    print("login resp:", resp[:200])
    assert json.loads(resp)["data"]["rc"] == 0
    connection.send(json.dumps({"action": "next", "data": {"seq": 1, "image": base64.b64encode(buffer.getvalue()).decode(), "instruction": scenes["living_room"]["instruction"]}}))
    first_prediction, waypoints = decode_response(connection.recv(), 1)
print("模型文本:", first_prediction.get("raw_text", ""))
print("停止标志:", first_prediction["stop"], "；轨迹形状:", waypoints.shape)
print("REPRO_OK")
