import socket
import threading
import json
import uuid
import base64
import os
import time
import zipfile
import subprocess

MASTER_DISCOVERY_PORT = 8888
HEARTBEAT_INTERVAL = 10
WORK_DIR = "work"

peer_id = str(uuid.uuid4())
master_ip = None
master_port = None

def discover_master():
    global master_ip, master_port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(5)
    msg = {
        "action": "DISCOVER_MASTER",
        "peer_id": peer_id,
        "port_tcp": 0
    }
    sock.sendto(json.dumps(msg).encode(), ("255.255.255.255", MASTER_DISCOVERY_PORT))
    try:
        data, addr = sock.recvfrom(4096)
        response = json.loads(data.decode())
        if response.get("action") == "MASTER_ANNOUNCE":
            master_ip = response["master_ip"]
            master_port = response["master_port"]
            print(f"[DISCOVERY] Master encontrado em {master_ip}:{master_port}")
    except socket.timeout:
        print("[DISCOVERY] Timeout procurando Master")
        exit(1)

def tcp_send(message):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((master_ip, master_port))
    s.send(json.dumps(message).encode())
    response = s.recv(65536).decode()
    s.close()
    return json.loads(response)

def register():
    addr = [socket.gethostbyname(socket.gethostname()), 0]
    msg = {
        "action": "REGISTER",
        "peer_id": peer_id,
        "addr": addr
    }
    res = tcp_send(msg)
    print(f"[REGISTER] Resposta: {res}")

def heartbeat_loop():
    while True:
        msg = {"action": "HEARTBEAT", "peer_id": peer_id}
        res = tcp_send(msg)
        print(f"[HEARTBEAT] Status: {res.get('status')}")
        time.sleep(HEARTBEAT_INTERVAL)

def request_task():
    msg = {"action": "REQUEST_TASK", "peer_id": peer_id}
    res = tcp_send(msg)
    if res.get("action") == "TASK_PACKAGE":
        os.makedirs(WORK_DIR, exist_ok=True)
        task_name = res["task_name"]
        zip_bytes = base64.b64decode(res["task_data"])
        zip_path = os.path.join(WORK_DIR, task_name)
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            extract_dir = os.path.join(WORK_DIR, task_name.replace(".zip", ""))
            zip_ref.extractall(extract_dir)
        run_task(extract_dir, task_name)

def run_task(path, original_name):
    try:
        result_path = os.path.join(path, "stdout.txt")
        error_path = os.path.join(path, "stderr.txt")
        with open(result_path, "w") as out, open(error_path, "w") as err:
            subprocess.run(["python", "main.py"], cwd=path, stdout=out, stderr=err)
        zip_name = os.path.join(WORK_DIR, original_name)
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            zipf.write(os.path.join(path, "stdout.txt"), arcname="stdout.txt")
            zipf.write(os.path.join(path, "stderr.txt"), arcname="stderr.txt")
        with open(zip_name, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        msg = {
            "action": "SUBMIT_RESULT",
            "peer_id": peer_id,
            "result_name": original_name,
            "result_data": encoded
        }
        res = tcp_send(msg)
        print(f"[RESULT] Enviado: {res}")
    except Exception as e:
        print(f"[TASK ERROR] {e}")

if __name__ == "__main__":
    discover_master()
    register()
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    while True:
        request_task()
        time.sleep(15)
