import socket
import threading
import json
import base64
import os
import time

TASKS_DIR = "tasks"
RESULTS_DIR = "results"
PORT_DISCOVERY = 8888  # UDP
PORT_TCP = 9000        # TCP

registered_peers = {}
lock = threading.Lock()

def udp_discovery():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_sock.bind(("", PORT_DISCOVERY))
    print(f"[UDP] Escutando DISCOVER_MASTER na porta {udp_sock}")

    while True:
        data, addr = udp_sock.recvfrom(4096)
        msg = json.loads(data.decode())
        if msg.get("action") == "DISCOVER_MASTER":
            response = {
                "action": "MASTER_ANNOUNCE",
                "master_ip": socket.gethostbyname(socket.gethostname()),
                "master_port": PORT_TCP
            }
            udp_sock.sendto(json.dumps(response).encode(), addr)

def handle_peer(conn, addr):
    try:
        data = conn.recv(65536).decode()
        msg = json.loads(data)
        action = msg.get("action")

        if action == "REGISTER":
            with lock:
                registered_peers[msg["peer_id"]] = msg["addr"]
            conn.send(json.dumps({"status": "REGISTERED"}).encode())

        elif action == "HEARTBEAT":
            conn.send(json.dumps({"status": "ALIVE"}).encode())
            print(f"Node: {conn}")

        elif action == "REQUEST_TASK":
            task_files = os.listdir(TASKS_DIR)
            if not task_files:
                conn.send(json.dumps({"action": "NO_TASK"}).encode())
                return
            task_name = task_files[0]
            with open(os.path.join(TASKS_DIR, task_name), "rb") as f:
                task_data = base64.b64encode(f.read()).decode()
            os.remove(os.path.join(TASKS_DIR, task_name))
            response = {
                "action": "TASK_PACKAGE",
                "task_name": task_name,
                "task_data": task_data
            }
            conn.send(json.dumps(response).encode())

        elif action == "SUBMIT_RESULT":
            result_data = base64.b64decode(msg["result_data"])
            result_path = os.path.join(RESULTS_DIR, msg["result_name"])
            with open(result_path, "wb") as f:
                f.write(result_data)
            conn.send(json.dumps({"status": "OK"}).encode())

        else:
            conn.send(json.dumps({"status": "UNKNOWN_ACTION"}).encode())

    except Exception as e:
        print(f"Erro no peer {addr}: {e}")
    finally:
        conn.close()

def tcp_server():
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.bind(("", PORT_TCP))
    tcp_sock.listen(5)
    print(f"[TCP] Escutando conexões na porta {PORT_TCP}")

    while True:
        conn, addr = tcp_sock.accept()
        threading.Thread(target=handle_peer, args=(conn, addr), daemon=True).start()

def ensure_dirs():
    os.makedirs(TASKS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

if __name__ == "__main__":
    ensure_dirs()
    threading.Thread(target=udp_discovery, daemon=True).start()
    tcp_server()
