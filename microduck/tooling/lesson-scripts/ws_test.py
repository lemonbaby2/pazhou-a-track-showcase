import websocket
import json

ws = websocket.create_connection("ws://127.0.0.1:8050", timeout=60, http_no_proxy=["127.0.0.1", "localhost"])
ws.send(json.dumps({"action": "login", "data": {"clientId": "manual-test"}}))
resp = ws.recv()
print("LOGIN RESP:", resp[:300])
assert json.loads(resp)["data"]["rc"] == 0
ws.close()
print("WS_LOGIN_OK")
