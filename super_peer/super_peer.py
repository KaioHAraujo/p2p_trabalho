import socket
import threading
import json
import time
import base64
import os
import shutil

# --- CONFIGURAÇÃO ---
FIXED_TCP_PORT = 50000
DISCOVERY_PORT = 50001 # Porta dedicada para a descoberta UDP
TASKS_DIR = 'tasks'
RESULTS_DIR = 'results'
PROCESSING_DIR = 'processing' # Diretório para tarefas em andamento

registered_peers = {}
lock = threading.Lock()

# Cria os diretórios necessários na inicialização
os.makedirs(TASKS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(PROCESSING_DIR, exist_ok=True)

def udp_discovery_listener():
    """
    Escuta por broadcasts UDP de peers procurando por um super-peer.
    Responde com o endereço IP e a porta TCP do super-peer.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', DISCOVERY_PORT))
        print(f"[DISCOVERY] Escutando por peers na porta UDP {DISCOVERY_PORT}")

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode())
                if message.get("action") == "DISCOVER_SUPER_PEER":
                    print(f"[DISCOVERY] Probe de descoberta recebido de {addr}")
                    # Determina o IP da máquina local que pode se comunicar com o peer
                    my_ip = socket.gethostbyname(socket.gethostname())
                    response = {
                        "action": "SUPER_PEER_ANNOUNCEMENT",
                        "ip": my_ip,
                        "port": FIXED_TCP_PORT
                    }
                    sock.sendto(json.dumps(response).encode(), addr)
            except (json.JSONDecodeError, UnicodeDecodeError):
                print(f"[DISCOVERY] Mensagem de descoberta inválida recebida.")
            except Exception as e:
                print(f"[DISCOVERY_ERROR] Erro no listener de descoberta: {e}")


def handle_peers(conn, addr):
    with conn:
        try:
            # Aumentar o buffer para acomodar dados de resultados em base64
            data = conn.recv(1048576).decode()
            if not data:
                return

            msg = json.loads(data)
            action = msg.get("action")
            peer_id = msg.get("peer_id")

            if action == "REGISTER":
                p2p_port = msg.get("p2p_port")
                with lock:
                    registered_peers[peer_id] = {"addr": addr, "last_seen": time.time(), "p2p_port": p2p_port}
                print(f"[REGISTER] {peer_id} registrado.")
                conn.send(json.dumps({"status": "REGISTERED"}).encode())

            elif action == "HEARTBEAT":
                with lock:
                    if peer_id in registered_peers:
                        registered_peers[peer_id]["last_seen"] = time.time()
                conn.send(json.dumps({"status": "ALIVE"}).encode())
           
            # --- IMPLEMENTAÇÃO DA LÓGICA DE TAREFAS ---

            elif action == "REQUEST_TASK":
                task_name = None
                with lock:
                    # Procura por uma tarefa disponível no diretório 'tasks'
                    available_tasks = [f for f in os.listdir(TASKS_DIR) if f.endswith('.zip')]
                    if available_tasks:
                        task_name = available_tasks[0]
                        # Move a tarefa para o diretório 'processing' para evitar dupla alocação
                        shutil.move(os.path.join(TASKS_DIR, task_name), os.path.join(PROCESSING_DIR, task_name))
               
                if task_name:
                    print(f"[TASK] Enviando tarefa '{task_name}' para {peer_id}")
                    task_path = os.path.join(PROCESSING_DIR, task_name)
                    with open(task_path, 'rb') as f:
                        task_bytes = f.read()
                   
                    task_data_b64 = base64.b64encode(task_bytes).decode('utf-8')
                    response = {
                        "action": "TASK_PACKAGE",
                        "task_name": task_name,
                        "task_data": task_data_b64
                    }
                else:
                    print(f"[TASK] Nenhuma tarefa disponível para {peer_id}")
                    response = {"action": "TASK_PACKAGE", "task_name": None, "task_data": None}
               
                conn.sendall(json.dumps(response).encode())

            elif action == "SUBMIT_RESULT":
                result_name = msg.get("result_name")
                result_data_b64 = msg.get("result_data")
               
                print(f"[RESULT] Recebido resultado para '{result_name}' de {peer_id}")
               
                # Decodifica e salva o arquivo de resultado
                result_bytes = base64.b64decode(result_data_b64)
                result_path = os.path.join(RESULTS_DIR, f"result_{result_name}")
                with open(result_path, 'wb') as f:
                    f.write(result_bytes)
                   
                # Remove a tarefa do diretório 'processing'
                with lock:
                    processing_path = os.path.join(PROCESSING_DIR, result_name)
                    if os.path.exists(processing_path):
                        os.remove(processing_path)

                conn.send(json.dumps({"status": "OK"}).encode())

            # --- Ações P2P existentes (sem modificação) ---
            elif action == "LIST_PEERS":
                with lock:
                    peer_list = [pid for pid in registered_peers if pid != peer_id]
                conn.send(json.dumps({"peers": peer_list}).encode())

            elif action == "GET_PEER_INFO":
                target_peer_id = msg.get("target_peer_id")
                with lock:
                    target_peer = registered_peers.get(target_peer_id)
                if target_peer:
                    target_ip, _ = target_peer["addr"]
                    response = {"status": "ok", "peer_id": target_peer_id, "peer_ip": target_ip, "peer_port": target_peer["p2p_port"]}
                else:
                    response = {"status": "error", "message": "Peer não encontrado"}
                conn.send(json.dumps(response).encode())

        except json.JSONDecodeError:
             print(f"[ERRO] Mensagem JSON inválida recebida de {addr}")
        except Exception as e:
            print(f"[ERRO] Conexão {addr}: {e}")

def tcp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', FIXED_TCP_PORT))
    sock.listen()
    print(f"[TCP] Super-Peer escutando na porta {FIXED_TCP_PORT}")

    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_peers, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    # Inicia a thread para escutar por conexões TCP principais
    listener_thread = threading.Thread(target=tcp_listener, daemon=True)
    listener_thread.start()

    # Inicia a thread para escutar por broadcasts de descoberta UDP
    discovery_thread = threading.Thread(target=udp_discovery_listener, daemon=True)
    discovery_thread.start()
   
    print("Super-Peer iniciado. Pressione Ctrl+C para sair.")
    while True:
        time.sleep(60)