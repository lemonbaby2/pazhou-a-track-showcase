import sys
sys.path.insert(0, "/home/nvidia/LightNav-0/mujoco_demo")
sys.path.insert(0, "/home/nvidia/microduck-course-run/topic/02-可运行代码/lightnav-learning")
import websocket
print("websocket module:", websocket.__file__)
print("has create_connection:", hasattr(websocket, "create_connection"))
import json
ws = websocket.create_connection("ws://127.0.0.1:8050", timeout=60, http_no_proxy=["127.0.0.1", "localhost"])
ws.send(json.dumps({"action": "login", "data": {"clientId": "path-test"}}))
print("LOGIN RESP:", ws.recv()[:200])
ws.close()
print("PATH_TEST_OK")
